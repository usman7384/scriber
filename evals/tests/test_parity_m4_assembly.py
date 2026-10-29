import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals.parity import Rig, run_row
from partwright_evals.parity_m4_assembly import FIXTURES, ROWS, fixture
from partwright_geometry import LocalGeometry
from partwright_ir import scope

ROOT = Path(__file__).parents[2]
NO_REQS = json.dumps({"requirements": []})


def text(name: str) -> str:
    return (FIXTURES / f"{name}.json").read_text(encoding="utf-8")


def vented_lid() -> str:
    lid: dict[str, Any] = scope(fixture("enclosure"), "lid").model_dump(mode="json")
    lid["params"] += [
        {"name": "vent_length", "value": 30, "unit": "mm"},
        {"name": "vent_width", "value": 3, "unit": "mm"},
        {"name": "vent_count", "value": 5, "unit": ""},
        {"name": "vent_pitch", "value": 6, "unit": "mm"},
    ]
    (part,) = lid["parts"]
    slot = {"kind": "slot", "center": [0, "-(vent_count - 1) * vent_pitch / 2"], "length": "vent_length", "width": "vent_width"}
    part["sketches"].append({"id": "vent", "plane": {"ref": "plate.end"}, "entities": [slot]})
    part["features"] += [
        {"kind": "extrude", "id": "vent", "name": "Vent slot", "sketch": "vent", "mode": "cut", "extent": "through_all"},
        {"kind": "pattern", "id": "vents", "name": "Vent slots", "features": ["vent"], "type": "linear", "count": "vent_count"}
        | {"direction": "y", "spacing": "vent_pitch"},
    ]
    return json.dumps({"updates": [], "design": lid})


ANSWERS: dict[str, list[str]] = {
    "GE-5": [NO_REQS, text("enclosure")],
    "GE-6": [NO_REQS, text("drone")],
    "PR-5": [NO_REQS, vented_lid()],
    "AS-3": [text("servo")],
}


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()


@pytest.mark.parametrize("row", sorted(ROWS))
def test_m4_assembly_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    rig = Rig(tmp_path, geometry, FakeLLM(ANSWERS.get(row, [])), load(ROOT / "config.yaml"))
    ev = run_row(row, ROWS[row], rig)
    assert ev.passed, ev
