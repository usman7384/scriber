import argparse
import json
import time
from pathlib import Path

import yaml
from pydantic import BaseModel

from partwright_agent import LLM, Requirement, check, generate
from partwright_cli.config import llm_for, load
from partwright_geometry import LocalGeometry


class Case(BaseModel):
    id: str
    rows: list[str]
    prompt: str
    checks: list[Requirement]


class CaseResult(BaseModel):
    id: str
    model: str
    built: bool
    valid: bool
    agent_ok: bool
    checks_passed: int
    checks_total: int
    failed_checks: list[str]
    attempts: int
    repairs: int
    seconds: float
    final_step: str


def load_cases(path: Path) -> list[Case]:
    return [Case.model_validate(c) for c in yaml.safe_load(path.read_text(encoding="utf-8"))]


def run_case(case: Case, llm: LLM, geometry: LocalGeometry, out_dir: Path) -> CaseResult:
    start = time.monotonic()
    steps = list(generate(case.prompt, llm, geometry, out_dir / case.id))
    final = steps[-1]
    r = final.result
    artifact = r.artifact if r else None
    results = check(case.checks, artifact) if artifact else []
    return CaseResult(
        id=case.id,
        model=llm.name,
        built=artifact is not None,
        valid=bool(artifact and artifact.ok),
        agent_ok=bool(r and r.ok),
        checks_passed=sum(c.passed for c in results),
        checks_total=len(case.checks),
        failed_checks=[f"{c.requirement.description}: {c.actual}" for c in results if not c.passed],
        attempts=r.attempts if r else 0,
        repairs=r.repairs if r else 0,
        seconds=round(time.monotonic() - start, 1),
        final_step=final.message[:300],
    )


def scorecard(results: list[CaseResult]) -> str:
    lines = ["| model | built | valid | checks | all checks pass | repairs | median s |", "|---|---|---|---|---|---|---|"]
    for model in sorted({r.model for r in results}):
        rs = [r for r in results if r.model == model]
        n = len(rs)
        checks = sum(r.checks_passed for r in rs), sum(r.checks_total for r in rs)
        secs = sorted(r.seconds for r in rs)[n // 2]
        perfect = sum(r.built and r.checks_passed == r.checks_total for r in rs)
        lines.append(
            f"| {model} | {sum(r.built for r in rs)}/{n} | {sum(r.valid for r in rs)}/{n} | {checks[0]}/{checks[1]} "
            f"| {perfect}/{n} | {sum(r.repairs for r in rs)} | {secs} |"
        )
    lines += ["", "| case | model | built | checks | repairs | s | failed checks |", "|---|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: (r.id, r.model)):
        failed = "; ".join(r.failed_checks) or ("-" if r.built else r.final_step)
        built = "yes" if r.built else "no"
        lines.append(f"| {r.id} | {r.model} | {built} | {r.checks_passed}/{r.checks_total} | {r.repairs} | {r.seconds} | {failed} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(prog="partwright-evals")
    p.add_argument("cases", type=Path)
    p.add_argument("--models", nargs="+", required=True)
    p.add_argument("--out", type=Path, default=Path("evals/results"))
    p.add_argument("--config", type=Path, default=Path("config.yaml"))
    args = p.parse_args()
    cases = load_cases(args.cases)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = args.out / f"{args.cases.stem}-{stamp}"
    results: list[CaseResult] = []
    config = load(args.config)
    geometry = LocalGeometry(timeout_s=config.geometry.timeout_s)
    try:
        for model in args.models:
            llm = llm_for(config, model)
            for case in cases:
                result = run_case(case, llm, geometry, run_dir / model.replace(":", "_"))
                results.append(result)
                print(json.dumps(result.model_dump()), flush=True)
    finally:
        geometry.close()
    (run_dir / "results.json").write_text(json.dumps([r.model_dump() for r in results], indent=2), encoding="utf-8")
    (run_dir / "SCORECARD.md").write_text(scorecard(results), encoding="utf-8")
    print(scorecard(results))


if __name__ == "__main__":
    main()
