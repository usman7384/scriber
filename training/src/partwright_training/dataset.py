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

from partwright_geometry import LocalGeometry
from partwright_training.context import grounding
from partwright_training.families import FAMILIES
from partwright_training.render import Prompt, render
from partwright_training.samples import Sample, generate_sample, repair_sample, requirement_sample
from partwright_training.spec import Spec
from partwright_training.verify import failures

HELDOUT_OFFSET = 500_000
PRIOR_OFFSET = 7_000_000
EVAL_CASES = ("evals/cases/m1.yaml", "evals/cases/challenge.yaml", "evals/grounded/cases.yaml")


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
            self._free.put(LocalGeometry())

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


def make(seed: int, pool: Pool, samples: bool, repair_rate: float, requirement_rate: float) -> Outcome:
    rng = random.Random(seed)
    family = list(FAMILIES)[seed % len(FAMILIES)]
    spec = FAMILIES[family](rng)
    prompt = render(spec, rng)
    context = grounding(spec, rng, FAMILIES[family](random.Random(seed + PRIOR_OFFSET)))
    out = Path(tempfile.mkdtemp(prefix="pw-ft-"))
    try:
        with pool.geometry() as g:
            problems = failures(spec, g, out / "verify")
            made: list[Sample] = []
            if samples and not problems:
                made.append(generate_sample(spec, prompt, context))
                if rng.random() < repair_rate and (repair := repair_sample(spec, prompt, context, g, out, rng)):
                    made.append(repair)
                if rng.random() < requirement_rate and (req := requirement_sample(spec, prompt)):
                    made.append(req)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    return Outcome(spec, prompt, problems, made)


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
    p.add_argument("--cases", type=Path, default=Path("evals/cases/synthetic.yaml"))
    args = p.parse_args()
    base = args.seed * 1_000_000
    pool = Pool(args.workers)
    try:
        with ThreadPoolExecutor(args.workers) as ex:
            train = list(ex.map(lambda s: make(s, pool, True, args.repair_rate, args.requirement_rate), range(base, base + args.specs)))
            held_seeds = range(base + HELDOUT_OFFSET, base + HELDOUT_OFFSET + args.heldout * 2)
            held = [o for o in ex.map(lambda s: make(s, pool, False, 0, 0), held_seeds) if not o.problems][: args.heldout]
    finally:
        pool.close()
    leaks = eval_ngrams(Path.cwd())
    kept = [s for o in train for s in o.samples if not _ngrams(s.messages[1][1]) & leaks]
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "train.jsonl").open("w", encoding="utf-8") as f:
        for s in kept:
            f.write(json.dumps(s.record()) + "\n")
    args.cases.write_text(
        "# Held-out synthetic cases from partwright-dataset (generator seeds disjoint from training). Regenerate, do not edit.\n"
        + yaml.safe_dump([case(o, i) for i, o in enumerate(held)], sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    card = _card(train, kept, len(held))
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
        "licence": "all generated by partwright-training; no third-party data",
    }


if __name__ == "__main__":
    main()
