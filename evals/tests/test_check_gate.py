import json
from pathlib import Path

from scriber_agent import FakeLLM
from scriber_evals.check_gate import false_checks
from scriber_evals.parity_m6 import SHOWCASE
from scriber_evals.run import load_cases
from scriber_geometry import LocalGeometry


def test_a_check_the_reference_part_fails_is_reported_as_false(tmp_path: Path) -> None:
    case = next(c for c in load_cases(SHOWCASE) if c.id == "sc03-keyed-shaft")
    misread = {"kind": "extent", "description": "journal 30 as an overall size", "value": 30}
    reqs = [{"kind": "extent", "description": "length 180", "value": 180}, misread]
    geometry = LocalGeometry(timeout_s=300)
    try:
        bad = false_checks(case, FakeLLM([json.dumps({"requirements": reqs})]), geometry, tmp_path)
    finally:
        geometry.close()
    assert [c.requirement.description for c in bad] == ["journal 30 as an overall size"]
