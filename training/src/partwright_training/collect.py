import argparse
import json
import random
import tempfile
from collections.abc import Iterator
from functools import partial
from pathlib import Path

from partwright_agent import LLM, Message, design_messages, evaluate, reference_data, repair_message
from partwright_cli.config import llm_for, load
from partwright_geometry import LocalGeometry
from partwright_ir import Design, json_schema
from partwright_training.context import RULES
from partwright_training.families import FAMILIES, S3_FAMILIES
from partwright_training.intent import intended
from partwright_training.names import renamed
from partwright_training.render import render
from partwright_training.samples import Sample, Task
from partwright_training.verify import failures

# keeps collected prompts apart from the dataset's training (+0), held-out (+500k) and prior (+7M) seeds
ONPOLICY_OFFSET = 3_000_000


def collect(seeds: range, llm: LLM, geometry: LocalGeometry, out_dir: Path, s3: bool = False) -> Iterator[Sample]:
    families = S3_FAMILIES if s3 else FAMILIES
    for seed in seeds:
        rng = random.Random(seed)
        family = list(families)[seed % len(families)]
        spec = renamed(families[family](rng), rng)
        spec = intended(spec) if s3 else spec
        prompt = render(spec, rng)
        if spec.exempt or failures(spec, geometry, out_dir / f"{seed}-verify"):
            continue
        task = Task(prompt, None, spec.design)
        asked = design_messages(prompt.text, reference_data(prompt.text), few_shot=llm.few_shot)
        raw = llm.chat([Message(role=r, content=c) for r, c in asked], json_schema(), 0, 0.0)
        build = partial(geometry.build, rules=RULES)
        problems, *_ = evaluate(raw, Design.model_validate_json, list(spec.checks), build, out_dir / str(seed), prompt.text)
        if problems:
            messages = (*task.messages(), ("user", repair_message(raw, problems)), ("assistant", task.answer()))
            yield Sample("repair", family, prompt.style, f"on-policy {llm.name}", messages)


def main() -> None:
    p = argparse.ArgumentParser(prog="partwright-collect")
    p.add_argument("--model", required=True)
    p.add_argument("--specs", type=int, default=300)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    p.add_argument("--s3", action="store_true", help="prompts from the S3 families, targets with feature intents")
    args = p.parse_args()
    llm = llm_for(load(args.config), args.model)
    base = args.seed * 1_000_000 + ONPOLICY_OFFSET
    geometry = LocalGeometry(timeout_s=600)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    try:
        with args.out.open("w", encoding="utf-8") as f, tempfile.TemporaryDirectory(prefix="pw-collect-") as tmp:
            for sample in collect(range(base, base + args.specs), llm, geometry, Path(tmp), args.s3):
                f.write(json.dumps(sample.record()) + "\n")
                f.flush()
                kept += 1
                print(f"{kept} failing answers kept", flush=True)
    finally:
        geometry.close()
    print(f"{kept} on-policy repairs from {args.specs} specs -> {args.out}")


if __name__ == "__main__":
    main()
