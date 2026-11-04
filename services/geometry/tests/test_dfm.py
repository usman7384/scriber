import math
from pathlib import Path
from typing import Any

import pytest

from scriber_geometry import Finding, LocalGeometry
from scriber_ir import Design, Process, Rule, RuleSet

EDGE = Rule(id="hole-edge", kind="min_hole_edge_ratio", value=1.5, unit="")
WALL = Rule(id="min-wall", kind="min_wall_thickness", value=1.0, unit="mm")
HOLE = Rule(id="min-hole", kind="min_hole_diameter", value=12, unit="mm")
SIZE = Rule(id="max-size", kind="max_overall_size", value=50, unit="mm")
CORNER = Rule(id="mill-corner", kind="min_internal_corner_radius", value=3, unit="mm", process="milling_3axis")
OVERHANG = Rule(id="fdm-overhang", kind="max_overhang_angle", value=45, unit="deg", process="fdm")


def part(sketches: list[dict[str, Any]], features: list[dict[str, Any]]) -> Design:
    return Design.model_validate(
        {"title": "Fixture", "params": [], "parts": [{"id": "p", "name": "P", "sketches": sketches, "features": features}]}
    )


def plate(hole_x: float) -> Design:
    hole = {
        "kind": "hole",
        "id": "h",
        "name": "Hole",
        "plane": {"offset": 5},
        "at": {"kind": "points", "points": [[hole_x, 0]]},
        "diameter": 10,
    }
    return part([{"id": "s", "entities": [{"kind": "rect", "width": 60, "height": 40}]}], [_extrude("s", 5), hole])


def pocket(corner_radius: float) -> Design:
    sketches: list[dict[str, Any]] = [
        {"id": "s", "entities": [{"kind": "rect", "width": 60, "height": 40}]},
        {"id": "k", "plane": {"offset": 20}, "entities": [{"kind": "rect", "width": 30, "height": 20, "corner_radius": corner_radius}]},
    ]
    return part(sketches, [_extrude("s", 20), {**_extrude("k", -10), "id": "pocket", "mode": "cut"}])


def box(wall: float) -> Design:
    shell = {"kind": "shell", "id": "shell", "name": "Shell", "open_face": "top", "thickness": wall}
    return part([{"id": "s", "entities": [{"kind": "rect", "width": 40, "height": 30}]}], [_extrude("s", 20), shell])


def ledge(underside_from_horizontal: float) -> Design:
    tip = 10 + 20 * math.tan(math.radians(underside_from_horizontal))
    outline = [[0, 0], [20, 0], [20, 10], [40, tip], [40, 35], [0, 35]]
    return part([{"id": "s", "plane": {"base": "XZ"}, "entities": [{"kind": "polygon", "points": outline}]}], [_extrude("s", 10)])


def _extrude(sketch: str, distance: float) -> dict[str, Any]:
    return {"kind": "extrude", "id": f"body_{sketch}", "name": "Body", "sketch": sketch, "distance": distance}


CASES: list[tuple[str, Design, Rule, Process, list[float]]] = [
    ("hole-edge-fail", plate(20), EDGE, "any", [10]),
    ("hole-edge-pass", plate(15), EDGE, "any", []),
    ("wall-fail", box(0.6), WALL, "any", [0.6]),
    ("wall-pass", box(2), WALL, "any", []),
    ("hole-diameter-fail", plate(15), HOLE, "any", [10]),
    ("hole-diameter-pass", plate(15), HOLE.model_copy(update={"value": 8}), "any", []),
    ("size-fail", plate(15), SIZE, "any", [60]),
    ("size-pass", plate(15), SIZE.model_copy(update={"value": 60}), "any", []),
    ("corner-sharp-fail", pocket(0), CORNER, "milling_3axis", [0, 0, 0, 0]),
    ("corner-small-fail", pocket(2), CORNER, "milling_3axis", [2, 2, 2, 2]),
    ("corner-pass", pocket(4), CORNER, "milling_3axis", []),
    ("corner-not-milling", pocket(0), CORNER, "fdm", []),
    ("overhang-fail", ledge(20), OVERHANG, "fdm", [70]),
    ("overhang-pass", ledge(45), OVERHANG, "fdm", []),
]


def dfm(geometry: LocalGeometry, design: Design, rules: list[Rule], process: Process, out: Path) -> tuple[bool, list[Finding]]:
    art = geometry.build(design, out, rules=RuleSet(rules=rules), process=process)
    assert all(f.rule_id in {r.id for r in rules} for f in art.findings), art.findings
    return art.ok, art.findings


@pytest.mark.parametrize(("design", "rule", "process", "measured"), [c[1:] for c in CASES], ids=[c[0] for c in CASES])
def test_check_passes_or_fails(
    geometry: LocalGeometry, tmp_path: Path, design: Design, rule: Rule, process: Process, measured: list[float]
) -> None:
    ok, findings = dfm(geometry, design, [rule], process, tmp_path)
    assert [f.measured for f in findings] == pytest.approx(measured, abs=1e-3)
    assert ok == (not measured)
    assert all(f.severity == "error" and f.binding == "static" and f.suggestion and f.location for f in findings)


def test_hole_near_edge_recommends_moving_it(geometry: LocalGeometry, tmp_path: Path) -> None:
    _, (f,) = dfm(geometry, plate(20), [EDGE], "any", tmp_path)
    assert f.required == pytest.approx(15) and f.part == "p"
    assert f.suggestion and f.suggestion.startswith("keep hole centres x between -15 and 15 and y between -5 and 5")
    assert f.location and f.location.point == pytest.approx((20, 0, 2.5))
    assert "10 mm" in f.message and "15 mm" in f.message


def test_dynamic_rule_only_warns(geometry: LocalGeometry, tmp_path: Path) -> None:
    ok, (f,) = dfm(geometry, ledge(20), [OVERHANG.model_copy(update={"binding": "dynamic"})], "fdm", tmp_path)
    assert ok and f.severity == "warning" and f.binding == "dynamic"


def test_sharp_corner_suggests_fillet_at_the_corner(geometry: LocalGeometry, tmp_path: Path) -> None:
    _, findings = dfm(geometry, pocket(0), [CORNER], "milling_3axis", tmp_path)
    corners = sorted((round(f.location.point[0]), round(f.location.point[1])) for f in findings if f.location)
    assert corners == [(-15, -10), (-15, 10), (15, -10), (15, 10)]
    assert all("parallel_z" in (f.suggestion or "") for f in findings)


def test_hole_edge_rule_skips_large_bores(geometry: LocalGeometry, tmp_path: Path) -> None:
    bore = part(
        [{"id": "s", "entities": [{"kind": "rect", "width": 60, "height": 40}]}],
        [
            _extrude("s", 5),
            {
                "kind": "hole",
                "id": "b",
                "name": "Bore",
                "plane": {"offset": 5},
                "at": {"kind": "points", "points": [[0, 0]]},
                "diameter": 20,
            },
        ],
    )
    ok, findings = dfm(geometry, bore, [EDGE], "any", tmp_path)
    assert ok and findings == []
