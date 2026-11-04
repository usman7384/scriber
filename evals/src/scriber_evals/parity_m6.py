import json
import statistics
import time
from pathlib import Path

from scriber_evals.parity import Evidence, Measured, Rig, evidence
from scriber_evals.run import Case, CaseResult, load_cases, run_case, scorecard

ROOT = Path(__file__).parents[2]
SHOWCASE = ROOT / "cases" / "showcase.yaml"
REFERENCE = ROOT / "parity" / "m6" / "reference"
CORRECT_SHARE = 0.75
MEDIAN_SECONDS = 120.0


def editable(case: Case) -> Case:
    return case.model_copy(update={"robust": case.params})


def correct(r: CaseResult) -> bool:
    return r.built and r.valid and r.checks_passed == r.checks_total


def attempt(rig: Rig, case: Case) -> CaseResult:
    agent = rig.config.agent
    r = run_case(editable(case), rig.llm, rig.geometry, rig.out, agent.max_repairs, agent.seed)
    if r.built:
        rig.geometry.thumbnail(rig.out / r.id / f"attempt_{r.attempts}" / "model.glb", rig.out / f"{r.id}.png", 512)
    return r


def recorded(rig: Rig, case: Case) -> CaseResult:
    start = time.monotonic()
    try:
        return attempt(rig, case)
    except Exception as e:  # a model-server error (e.g. CUDA out of memory) fails this case, not the benchmark
        total = len(case.checks) + len(case.shape) + 2 * len(case.params)
        error = f"{type(e).__name__}: {e}"[:300]
        seconds = round(time.monotonic() - start, 1)
        return CaseResult(
            id=case.id,
            model=rig.llm.name,
            built=False,
            valid=False,
            agent_ok=False,
            checks_passed=0,
            checks_total=total,
            failed_checks=[error],
            attempts=0,
            repairs=0,
            seconds=seconds,
            final_step=error,
        )


def showcase(rig: Rig) -> Evidence:
    results = [recorded(rig, c) for c in load_cases(SHOWCASE)]
    (rig.out / "results.json").write_text(json.dumps([r.model_dump() for r in results], indent=2), encoding="utf-8")
    (rig.out / "SCORECARD.md").write_text(scorecard(results), encoding="utf-8")
    passed = [r.id for r in results if correct(r)]
    editable_parts = sum(r.built and not any(f.startswith("robust") for f in r.failed_checks) for r in results)
    median = statistics.median(r.seconds for r in results)
    measured: Measured = {
        "fully_correct": f"{len(passed)}/{len(results)}",
        "editable": f"{editable_parts}/{len(results)}",
        "median_s": median,
        "failed": ", ".join(r.id for r in results if r.id not in passed),
    }
    return evidence("M6-SHOWCASE", measured, len(passed) >= CORRECT_SHARE * len(results), median < MEDIAN_SECONDS)


ROWS = {"M6-SHOWCASE": showcase}
