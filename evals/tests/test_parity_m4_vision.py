import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from scriber_agent import FakeLLM
from scriber_cli.config import load
from scriber_evals import parity_m4_vision
from scriber_evals.parity import Rig, run_row
from scriber_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]
NO_REQS = json.dumps({"requirements": []})


def design(title: str, params: dict[str, float], sketches: list[dict[str, Any]], features: list[dict[str, Any]]) -> str:
    part = {"id": "part", "name": title, "sketches": sketches, "features": features}
    return json.dumps({"title": title, "params": [{"name": n, "value": v, "unit": "mm"} for n, v in params.items()], "parts": [part]})


def extrude(fid: str, sketch: str, distance: str, **extra: Any) -> dict[str, Any]:
    return {"kind": "extrude", "id": fid, "name": fid.title(), "sketch": sketch, "distance": distance, **extra}


def hole(fid: str, offset: str | float, at: dict[str, Any], diameter: str) -> dict[str, Any]:
    return {"kind": "hole", "id": fid, "name": fid.title(), "plane": {"offset": offset}, "at": at, "diameter": diameter}


def points(*xy: tuple[float, float]) -> dict[str, Any]:
    return {"kind": "points", "points": [list(p) for p in xy]}


PROFILE = [[0, 0], ["length", 0], ["length", "thickness"], ["thickness", "thickness"], ["thickness", "upright"], [0, "upright"]]
L_BRACKET = design(
    "L-bracket",
    {"length": 120, "width": 40, "thickness": 4, "upright": 30, "hole_d": 6},
    [{"id": "p", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": PROFILE}]}],
    [extrude("body", "p", "width", extent="symmetric"), hole("holes", 0, points((40, 0), (90, 0)), "hole_d")],
)
SERVO = design(
    "Micro servo",
    {"body_length": 22.2, "body_width": 11.8, "body_height": 22.7, "tab_length": 32.2, "tab_t": 2.5, "tab_top": 18.4, "hole_d": 2},
    [
        {"id": "b", "entities": [{"kind": "rect", "width": "body_length", "height": "body_width"}]},
        {"id": "t", "plane": {"offset": "tab_top - tab_t"}, "entities": [{"kind": "rect", "width": "tab_length", "height": "body_width"}]},
        {"id": "s", "plane": {"offset": "body_height"}, "entities": [{"kind": "circle", "center": [-5.2, 0], "diameter": 4.8}]},
    ],
    [
        extrude("body", "b", "body_height"),
        extrude("tabs", "t", "tab_t"),
        extrude("shaft", "s", "4"),
        hole("tab_holes", "tab_top", points((-13.9, 0), (13.9, 0)), "hole_d"),
    ],
)
FLANGE = design(
    "Flange",
    {"od": 120, "pcd": 90, "bolt_count": 6, "hole_d": 11, "hub_d": 60, "bore_d": 30, "flange_t": 12, "hub_len": 20},
    [
        {"id": "d", "entities": [{"kind": "circle", "diameter": "od"}]},
        {"id": "h", "plane": {"offset": "flange_t"}, "entities": [{"kind": "circle", "diameter": "hub_d"}]},
    ],
    [
        extrude("disc", "d", "flange_t"),
        extrude("hub", "h", "hub_len"),
        hole("bore", "flange_t + hub_len", points((0, 0)), "bore_d"),
        hole("bolts", "flange_t", {"kind": "polar", "count": "bolt_count", "diameter": "pcd"}, "hole_d"),
    ],
)
RIGHT = json.dumps({"findings": [], "matches": True})
WRONG = json.dumps({"findings": ["one of the holes the request asks for is missing"], "matches": False})
ANSWERS: dict[str, tuple[list[str], list[str]]] = {
    "IN-4": ([NO_REQS], [L_BRACKET]),
    "IN-5": ([NO_REQS], [SERVO]),
    "IN-6": ([NO_REQS], [FLANGE]),
    "VM-10": ([], [RIGHT, WRONG] * 5),
}


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()


@pytest.mark.parametrize("row", sorted(parity_m4_vision.ROWS))
def test_m4_vision_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text, images = ANSWERS[row]
    vision = FakeLLM(images)
    monkeypatch.setattr(parity_m4_vision, "vision_llm", lambda rig: vision)
    ev = run_row(row, parity_m4_vision.ROWS[row], Rig(tmp_path, geometry, FakeLLM(text), load(ROOT / "config.yaml")))
    assert ev.passed, ev
    assert vision.calls and all(call[-1].images for call in vision.calls)
