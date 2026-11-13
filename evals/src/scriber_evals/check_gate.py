import argparse
import sys
from pathlib import Path

from scriber_agent import LLM, CheckResult, check, extract_requirements
from scriber_cli.config import llm_for, load
from scriber_evals.parity_m6 import REFERENCE, SHOWCASE
from scriber_evals.run import Case, load_cases
from scriber_geometry import LocalGeometry
from scriber_ir import Design


def false_checks(case: Case, llm: LLM, geometry: LocalGeometry, out: Path) -> list[CheckResult]:
    # the reference part is correct by construction, so any extracted requirement it fails was misread
    reference = Design.model_validate_json((REFERENCE / f"{case.id}.json").read_text(encoding="utf-8"))
    reqs = extract_requirements(case.prompt, llm)
    return [c for c in check(reqs, geometry.build(reference, out / case.id)) if not c.passed]


def main() -> None:
    p = argparse.ArgumentParser(prog="scriber-check-gate", description="Find requirement checks that fail on known-correct parts")
    p.add_argument("--model", help="the requirement extractor; defaults to llm.default")
    p.add_argument("--ids", nargs="*", default=[], help="only these showcase cases")
    p.add_argument("--out", type=Path, default=Path("evals/results/check-gate"))
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = p.parse_args()
    config = load(args.config)
    llm = llm_for(config, args.model)
    cases = [c for c in load_cases(SHOWCASE) if not args.ids or c.id in args.ids]
    geometry = LocalGeometry(timeout_s=config.geometry.timeout_s)
    found = 0
    try:
        for case in cases:
            bad = false_checks(case, llm, geometry, args.out)
            found += len(bad)
            print(
                f"{case.id}: {len(bad)} false" + "".join(f"\n  {c.requirement.description} (actual: {c.actual})" for c in bad), flush=True
            )
    finally:
        geometry.close()
    print(f"{found} false checks over {len(cases)} reference parts")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
