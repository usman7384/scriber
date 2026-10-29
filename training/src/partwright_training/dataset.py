import argparse
import json
import queue
import random
import shutil
import tempfile
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from partwright_agent import OllamaLLM, misquoted
from partwright_geometry import LocalGeometry
from partwright_training.context import documented, edited, grounding, tabled
from partwright_training.families import FAMILIES, S3_FAMILIES
from partwright_training.intent import intended
from partwright_training.names import renamed
from partwright_training.paraphrase import REGISTERS, Paraphraser, defaults, requote
from partwright_training.render import Prompt, exposing, render
from partwright_training.samples import Sample, Task, generate_sample, repair_sample, requirement_sample
from partwright_training.spec import Spec
from partwright_training.verify import design_failures, failures

HELDOUT_OFFSET = 500_000
PRIOR_OFFSET = 7_000_000
DOCUMENTED, VAGUE, PARAPHRASED, EDIT = 0.15, 0.15, 0.45, 0.08
# share of hole-table parts asked for with the table in the project documents instead of the request
TABLED = 0.4
# S3 requests that name a few parameters to expose, as the showcase prompts do
EXPOSED = 0.3
EVAL_CASES = (
    "evals/cases/m1.yaml",
    "evals/cases/challenge.yaml",
    "evals/grounded/cases.yaml",
    "evals/cases/dev.yaml",
    "evals/cases/parts.yaml",
    "evals/cases/benchmark.yaml",
    "evals/cases/conventions.yaml",
    "evals/cases/showcase.yaml",
)


@dataclass(frozen=True)
class Outcome:
    spec: Spec
    prompt: Prompt
    problems: list[str]
    samples: list[Sample]


class Pool:
    def __init__(self, size: int) -> None:
        self._free: queue.Queue[LocalGeometry] = queue.Queue()
        for _ in range(size):
            self._free.put(LocalGeometry(timeout_s=180))

    @contextmanager
    def geometry(self) -> Iterator[LocalGeometry]:
        g = self._free.get()
        try:
            yield g
        finally:
            self._free.put(g)

    def close(self) -> None:
        while not self._free.empty():
            self._free.get().close()


def make(
    seed: int, pool: Pool, para: Paraphraser | None, samples: bool, repair_rate: float, requirement_rate: float, s3: bool = False
) -> Outcome:
    rng = random.Random(seed)
    families = S3_FAMILIES if s3 else FAMILIES
    family = list(families)[seed % len(families)]
    spec = renamed(families[family](rng), rng)
    spec = intended(spec) if s3 else spec
    prompt = render(spec, rng)
    if s3 and prompt.style != "spec" and rng.random() < EXPOSED:
        prompt = exposing(prompt, spec, rng)
    out = Path(tempfile.mkdtemp(prefix="pw-ft-"))
    try:
        with pool.geometry() as g:
            problems = failures(spec, g, out / "verify")
            made: list[Sample] = []
            if samples and not problems:
                edit = edit_task(spec, rng, g, out) if not spec.exempt and not spec.positions and rng.random() < EDIT else None
                prior = families[family](random.Random(seed + PRIOR_OFFSET))
                task = edit or variant(spec, prompt, rng, para, intended(prior) if s3 else prior, seed)
                prompt = task.prompt
                if bad := misquoted(task.design, prompt.text):
                    return Outcome(spec, prompt, [f"misquoted: {bad[0][:100]}"], [])
                made.append(generate_sample(spec, task))
                plain = edit is None and not spec.exempt
                if plain and rng.random() < repair_rate and (repair := repair_sample(spec, task, g, out, rng)):
                    made.append(repair)
                if edit is None and rng.random() < requirement_rate and (req := requirement_sample(spec, prompt)):
                    made.append(req)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    return Outcome(spec, prompt, problems, made)


def edit_task(spec: Spec, rng: random.Random, g: LocalGeometry, out: Path) -> Task | None:
    made = edited(spec, rng)
    if made is None:
        return None
    prompt, context, design, checks = made
    return None if design_failures(design, checks, spec.exempt, g, out / "edit") else Task(prompt, context, design)


def variant(spec: Spec, prompt: Prompt, rng: random.Random, para: Paraphraser | None, prior: Spec, seed: int) -> Task:
    roll = rng.random()
    if spec.exempt:
        # a standard part that breaks a default rule must not meet that rule in a project context
        return Task(prompt, None, spec.design)
    if spec.positions:
        # a hole table is never paraphrased or reduced to facts one value at a time
        table = tabled(spec, rng) if roll < TABLED else None
        return Task(*table) if table else Task(prompt, grounding(spec, rng, prior), spec.design)
    if roll < DOCUMENTED:
        return Task(*documented(spec, rng))
    context = grounding(spec, rng, prior)
    if para is not None and roll < DOCUMENTED + VAGUE and (text := para.vague(prompt.text, seed)):
        return Task(Prompt("vague", text), context, defaults(spec.design))
    if para is not None and prompt.style != "spec" and roll < DOCUMENTED + VAGUE + PARAPHRASED:
        for register in rng.sample(list(REGISTERS), 2):
            text = para.rewrite(prompt.text, register, seed)
            requoted = requote(spec.design, prompt.text, text) if text else None
            if text and requoted:
                return Task(Prompt(f"para-{register}", text), context, requoted)
    return Task(prompt, context, spec.design)


def eval_ngrams(root: Path, n: int = 8) -> set[tuple[str, ...]]:
    grams: set[tuple[str, ...]] = set()
    for path in EVAL_CASES:
        for case in yaml.safe_load((root / path).read_text(encoding="utf-8")):
            grams |= _ngrams(case.get("prompt") or case["request"], n)
    return grams


def _ngrams(text: str, n: int = 8) -> set[tuple[str, ...]]:
    words = text.lower().split()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def case(o: Outcome, index: int) -> dict[str, Any]:
    return {
        "id": f"s0-{o.spec.family}-{index:03d}",
        "rows": ["FT-1"],
        "prompt": o.prompt.text,
        "checks": [c.model_dump(mode="json", exclude_defaults=True) for c in o.spec.checks],
        "params": list(o.prompt.required_params),
    }


def main() -> None:
    p = argparse.ArgumentParser(prog="partwright-dataset")
    p.add_argument("--specs", type=int, default=1300)
    p.add_argument("--heldout", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--repair-rate", type=float, default=0.5)
    p.add_argument("--requirement-rate", type=float, default=0.25)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", type=Path, default=Path("data/training/s0"))
    p.add_argument("--cases", type=Path, help="write the held-out cases here (evals/cases/synthetic.yaml)")
    p.add_argument("--paraphrase-model", help="local Ollama model that rewrites prompts, e.g. qwen3.5:4b")
    p.add_argument("--onpolicy", type=Path, nargs="*", default=[], help="repair samples from partwright-collect to merge in")
    p.add_argument(
        "--s3", action="store_true", help="add the S3 families (gears, shafts, housings, assemblies, hole tables) and feature intents"
    )
    args = p.parse_args()
    base = args.seed * 1_000_000
    pool = Pool(args.workers)
    args.out.mkdir(parents=True, exist_ok=True)
    para = None
    if args.paraphrase_model:
        llm = OllamaLLM(args.paraphrase_model, num_ctx=4096, think=False, max_tokens=1200)
        para = Paraphraser(llm, args.out.parent / "paraphrase_cache.jsonl")
    try:
        with ThreadPoolExecutor(args.workers) as ex:
            seeds = range(base, base + args.specs)
            train = list(ex.map(lambda s: make(s, pool, para, True, args.repair_rate, args.requirement_rate, args.s3), seeds))
            held_seeds = range(base + HELDOUT_OFFSET, base + HELDOUT_OFFSET + args.heldout * 2) if args.cases else range(0)
            held = [o for o in ex.map(lambda s: make(s, pool, None, False, 0, 0, args.s3), held_seeds) if not o.problems][: args.heldout]
    finally:
        pool.close()
    leaks = eval_ngrams(Path.cwd())
    merged = [s for o in train for s in o.samples] + [s for path in args.onpolicy for s in _load(path)]
    kept = [s for s in merged if not _ngrams(s.messages[1][1]) & leaks]
    with (args.out / "train.jsonl").open("w", encoding="utf-8") as f:
        for s in kept:
            f.write(json.dumps(s.record()) + "\n")
    if args.cases:
        args.cases.write_text(
            "# Held-out synthetic cases from partwright-dataset (generator seeds disjoint from training). Regenerate, do not edit.\n"
            + yaml.safe_dump([case(o, i) for i, o in enumerate(held)], sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    card = _card(train, kept, len(held))
    if args.s3:
        card["s3"] = _s3_coverage(kept)
    (args.out / "card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(json.dumps(card, indent=2))


def _card(train: list[Outcome], kept: list[Sample], heldout: int) -> dict[str, Any]:
    rejected = Counter(f"{o.spec.family}: {o.problems[0][:120]}" for o in train if o.problems)
    return {
        "specs": len(train),
        "verified": sum(not o.problems for o in train),
        "rejected": dict(rejected.most_common(20)),
        "samples": len(kept),
        "by_kind": dict(Counter(s.kind for s in kept)),
        "by_family": dict(Counter(s.family for s in kept)),
        "by_style": dict(Counter(s.style for s in kept)),
        "with_context": dict(Counter(s.detail or "none" for s in kept if s.kind == "generate")),
        "repairs": dict(Counter(s.detail for s in kept if s.kind == "repair")),
        "heldout_cases": heldout,
        "coverage": _coverage(kept),
        "licence": "all generated by partwright-training; no third-party data",
    }


def _s3_coverage(kept: list[Sample]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for s in kept:
        if s.kind != "generate":
            continue
        design = json.loads(s.messages[-1][1])
        features = [f for part in design["parts"] for f in part["features"]]
        c["features"] += len(features)
        c["features with intent"] += sum(bool(f.get("intent")) for f in features)
        c["lid mates (implied joints)"] += sum(f["kind"] == "lid" for f in features)
        if len(design["parts"]) > 1:
            c[f"assemblies of {len(design['parts'])} parts"] += 1
        c.update(f"joint {j.get('kind', 'fastened')}" for j in (design.get("assembly") or {}).get("joints", []))
        if s.family == "table":
            c["hole table in the project documents" if s.style == "documented-table" else "hole table in the request"] += 1
    return dict(sorted(c.items()))


def _load(path: Path) -> list[Sample]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [Sample(r["kind"], r["family"], r["style"], r["detail"], tuple((m["role"], m["content"]) for m in r["messages"])) for r in rows]


def _coverage(kept: list[Sample]) -> dict[str, Any]:
    c: Counter[str] = Counter()
    titles, names = set(), set()
    for s in kept:
        if s.kind != "generate":
            continue
        design = json.loads(s.messages[-1][1])
        titles.add(design["title"])
        names |= {p["name"] for p in design["params"]}
        for part in design["parts"]:
            c.update(f"entity {e['kind']}" for sk in part["sketches"] for e in sk["entities"])
            for f in part["features"]:
                c[f"feature {f['kind']}"] += 1
                if f["kind"] == "hole":
                    c[f"placement {f['at']['kind']}"] += 1
                    c["hole by diameter" if "diameter" in f and "fastener" not in f else "hole by fastener"] += 1
                if f["kind"] == "extrude":
                    c[f"extrude {f.get('extent', 'blind')}/{f.get('mode', 'add')}"] += 1
                if f["kind"] == "pattern":
                    c[f"pattern {f['type']}"] += 1
    held_out = sum(any(w in s.messages[1][1] for w in ("DN50", "NEMA 17", "NEMA 23", "2020")) for s in kept)
    return {"titles": len(titles), "param_names": len(names), "eval_sizes_in_prompts": held_out, **dict(sorted(c.items()))}


if __name__ == "__main__":
    main()
