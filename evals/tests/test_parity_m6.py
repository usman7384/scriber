import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_context import DEFAULT_RULES
from partwright_evals import parity_m6
from partwright_evals.parity import Rig, run_row
from partwright_evals.parity_m6 import REFERENCE, ROWS, SHOWCASE, attempt, correct
from partwright_evals.run import load_cases
from partwright_evals.shapes import ShapeCheck, shape_check
from partwright_geometry import LocalGeometry
from partwright_ir import Design, apply_params

ROOT = Path(__file__).parents[2]
NO_REQS = json.dumps({"requirements": []})
CASES = {c.id: c for c in load_cases(SHOWCASE)}
DEMO = ["sc09-electronics-enclosure", "sc15-hub-gear", "sc20-flange-bearing"]
RULES = DEFAULT_RULES.for_process("any")


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=300)
    yield g
    g.close()


def reference(case_id: str) -> str:
    return (REFERENCE / f"{case_id}.json").read_text(encoding="utf-8")


def rig(out: Path, geometry: LocalGeometry, answers: list[str]) -> Rig:
    out.mkdir(parents=True, exist_ok=True)
    return Rig(out, geometry, FakeLLM(answers), load(ROOT / "config.yaml"))


def subset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ids: list[str]) -> None:
    cases = [c for c in yaml.safe_load(SHOWCASE.read_text(encoding="utf-8")) if c["id"] in ids]
    path = tmp_path / "showcase.yaml"
    path.write_text(yaml.safe_dump(cases), encoding="utf-8")
    monkeypatch.setattr(parity_m6, "SHOWCASE", path)


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_reference_design_builds_and_passes_its_own_checks(case_id: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    r = attempt(rig(tmp_path, geometry, [NO_REQS, reference(case_id)]), CASES[case_id])
    assert correct(r), r.failed_checks or r.final_step
    assert r.checks_total == len(CASES[case_id].checks) + len(CASES[case_id].shape) + 2 * len(CASES[case_id].params)
    assert (tmp_path / f"{case_id}.png").exists()


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_reference_and_its_edits_meet_the_default_rules(case_id: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    design = Design.model_validate_json(reference(case_id))
    values = design.param_values()
    edits = {n: apply_params(design, {n: values[n] * 1.05}) for n in CASES[case_id].params}
    for name, d in {"reference": design, **edits}.items():
        errors = [f.message for f in geometry.build(d, tmp_path / name, RULES).findings if f.severity == "error"]
        assert errors == [], name


def test_showcase_demo_passes_on_reference_answers(geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subset(tmp_path, monkeypatch, DEMO)
    answers = [a for c in DEMO for a in (NO_REQS, reference(c))]
    demo = rig(tmp_path / "run", geometry, answers)
    ev = run_row("M6-SHOWCASE", ROWS["M6-SHOWCASE"], demo)
    assert ev.passed, ev
    assert ev.measured["fully_correct"] == "3/3" and ev.measured["editable"] == "3/3"
    assert isinstance(demo.llm, FakeLLM) and demo.llm.responses == []
    assert len(json.loads((tmp_path / "run" / "M6-SHOWCASE" / "results.json").read_text(encoding="utf-8"))) == 3


def test_showcase_demo_fails_below_three_quarters(geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subset(tmp_path, monkeypatch, DEMO)
    swapped = [reference(DEMO[0]), reference(DEMO[2]), reference(DEMO[2])]
    ev = run_row("M6-SHOWCASE", ROWS["M6-SHOWCASE"], rig(tmp_path / "run", geometry, [a for s in swapped for a in (NO_REQS, s)]))
    assert not ev.passed
    assert ev.measured["fully_correct"] == "2/3" and ev.measured["failed"] == "sc15-hub-gear"


def test_teeth_check_reads_the_built_gear(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(Design.model_validate_json(reference("sc01-gear-pair")), tmp_path)
    teeth = {"kind": "teeth", "description": "pinion", "count": 20, "value": 44}
    assert shape_check(ShapeCheck.model_validate(teeth), art)[0]
    assert not shape_check(ShapeCheck.model_validate(teeth | {"count": 21}), art)[0]
    assert not shape_check(ShapeCheck.model_validate(teeth | {"value": 46}), art)[0]
    assert not shape_check(ShapeCheck(kind="mates", description="two joints", count=2), art)[0]
