import argparse
import json
import random
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from partwright_agent import misquoted
from partwright_training.dataset import Outcome, Pool, _card, _ngrams, eval_ngrams
from partwright_training.house import HOUSE
from partwright_training.render import STYLES, render
from partwright_training.samples import Sample, Task, generate_sample, repair_sample
from partwright_training.verify import failures

# the spec-sheet style lists the parameter names, which would state the naming convention in the request
PLAIN_STYLES = tuple(s for s in STYLES if s != "spec")


def make(seed: int, pool: Pool, repair_rate: float) -> Outcome:
    rng = random.Random(seed)
    spec = list(HOUSE.values())[seed % len(HOUSE)](rng)
    prompt = render(spec, rng, rng.choice(PLAIN_STYLES))
    out = Path(tempfile.mkdtemp(prefix="pw-cx-"))
    try:
        with pool.geometry() as g:
            problems = failures(spec, g, out / "verify") or [f"misquoted: {q[:100]}" for q in misquoted(spec.design, prompt.text)[:1]]
            made: list[Sample] = []
            if not problems:
                task = Task(prompt, None, spec.design)
                made.append(generate_sample(spec, task))
                if rng.random() < repair_rate and (repair := repair_sample(spec, task, g, out, rng)):
                    made.append(repair)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    return Outcome(spec, prompt, problems, made)


def main() -> None:
    p = argparse.ArgumentParser(prog="partwright-conventions", description="house-style corpus for CX-13 (evals/parity/m5/house-style.md)")
    p.add_argument("--specs", type=int, default=1000)
    p.add_argument("--seed", type=int, default=13)
    p.add_argument("--repair-rate", type=float, default=0.5)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--out", type=Path, default=Path("data/training/cx13"))
    args = p.parse_args()
    base = args.seed * 1_000_000
    pool = Pool(args.workers)
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(args.workers) as ex:
            train = list(ex.map(lambda s: make(s, pool, args.repair_rate), range(base, base + args.specs)))
    finally:
        pool.close()
    leaks = eval_ngrams(Path.cwd())
    kept = [s for o in train for s in o.samples if not _ngrams(s.messages[1][1]) & leaks]
    with (args.out / "train.jsonl").open("w", encoding="utf-8") as f:
        f.writelines(json.dumps(s.record()) + "\n" for s in kept)
    card = _card(train, kept, 0)
    (args.out / "card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(json.dumps(card, indent=2))


if __name__ == "__main__":
    main()
