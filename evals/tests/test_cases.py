from pathlib import Path

from partwright_evals.run import CaseResult, load_cases, scorecard

CASES = Path(__file__).parents[1] / "cases" / "m1.yaml"


def test_m1_cases_load_with_unique_ids() -> None:
    cases = load_cases(CASES)
    assert len(cases) == 10
    assert len({c.id for c in cases}) == 10
    assert all(c.checks for c in cases)


def test_scorecard_summarises_per_model() -> None:
    r = CaseResult(
        id="a",
        model="m",
        built=True,
        valid=True,
        agent_ok=True,
        checks_passed=2,
        checks_total=3,
        failed_checks=["x"],
        attempts=2,
        repairs=1,
        seconds=10.0,
        final_step="",
    )
    card = scorecard([r, r.model_copy(update={"id": "b", "checks_passed": 3})])
    assert "| m | 2/2 | 2/2 | 5/6 | 1/2 | 2 | 10.0 |" in card
