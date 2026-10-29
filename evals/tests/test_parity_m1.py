import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals.parity import Rig, run_row
from partwright_evals.parity_m1 import FIXTURES, ROWS
from partwright_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]
NO_REQS = json.dumps({"requirements": []})


def plate(name: str, length: float, width: float, thick: float, holes: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": name,
        "name": name.title(),
        "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": length, "height": width}]}],
        "features": [
            {"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": thick},
            {"kind": "hole", "id": "holes", "name": "Holes", "plane": {"offset": thick}, **holes},
        ],
    }


def design(title: str, params: list[tuple[str, float]], *parts: dict[str, Any]) -> str:
    return json.dumps({"title": title, "params": [{"name": n, "value": v, "unit": "mm"} for n, v in params], "parts": list(parts)})


GRID = {"at": {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "spacing_x", "spacing_y": "spacing_y"}, "diameter": "hole_d"}
BRACKET = design("Mounting bracket", [("spacing_x", 60), ("spacing_y", 40), ("hole_d", 6.6)], plate("bracket", 80, 60, 5, GRID))
TUBE = (FIXTURES / "tube.json").read_text(encoding="utf-8")
ADAPTER = design(
    "Flanged adapter",
    [("spacing_x", 85), ("spacing_y", 60), ("hole_d", 8.5)],
    {
        **plate("flange", 110, 80, 8, GRID),
        "sketches": [
            {"id": "s", "entities": [{"kind": "rect", "width": 110, "height": 80}]},
            {
                "id": "ring",
                "plane": {"offset": 8},
                "entities": [{"kind": "circle", "diameter": 40}, {"kind": "circle", "diameter": 30, "subtract": True}],
            },
        ],
        "features": [
            *plate("flange", 110, 80, 8, GRID)["features"],
            {"kind": "extrude", "id": "tube", "name": "Tube", "sketch": "ring", "distance": 52},
        ],
    },
)
GUSSET = {"id": "g", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": [[-20, 5], [20, 5], [-20, 45]]}]}
ANGLED = design(
    "Angled bracket",
    [("spacing_x", 50), ("spacing_y", 30), ("hole_d", 5.5)],
    {
        **plate("bracket", 70, 50, 5, GRID),
        "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": 70, "height": 50}]}, GUSSET],
        "features": [
            *plate("bracket", 70, 50, 5, GRID)["features"],
            {"kind": "extrude", "id": "gusset", "name": "Gusset", "sketch": "g", "extent": "symmetric", "distance": 5},
        ],
    },
)
L_BRACKET = design(
    "L-bracket",
    [("hole_d", 6)],
    plate("bracket", 120, 40, 4, {"at": {"kind": "points", "points": [[-45, -10], [-45, 10], [45, -10], [45, 10]]}, "diameter": "hole_d"}),
)
ANSWERS: dict[str, list[str]] = {
    "IN-1": [NO_REQS, TUBE],
    "DP-5": [NO_REQS, TUBE],
    "GE-7": [NO_REQS, BRACKET] * 5,
    "GE-10": [NO_REQS, TUBE, NO_REQS, BRACKET],
    "PR-4": [NO_REQS, json.dumps({"updates": [{"name": "length", "value": 450}], "design": None})],
    "DP-2": [NO_REQS, ADAPTER],
    "DP-7": [NO_REQS, ANGLED],
    "DP-21": [NO_REQS, L_BRACKET],
}


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()


@pytest.mark.parametrize("row", sorted(ROWS))
def test_m1_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    rig = Rig(tmp_path, geometry, FakeLLM(ANSWERS.get(row, [])), load(ROOT / "config.yaml"))
    ev = run_row(row, ROWS[row], rig)
    assert ev.passed, ev
