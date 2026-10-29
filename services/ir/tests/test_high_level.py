import math
from typing import Any

import pytest

from partwright_ir import Design, compile_design, joint_tree, validate
from partwright_ir.fasteners import screw_holes
from partwright_ir.gear import gear_flank, gear_problems, involute
from partwright_ir.keys import din6885


def part(pid: str, *features: dict[str, Any], sketches: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"id": pid, "name": pid.title(), "sketches": sketches or [], "features": list(features)}


def design(*parts: dict[str, Any], **extra: Any) -> Design:
    return Design.model_validate({"title": "T", "params": [], "parts": list(parts), **extra})


def gear(**over: Any) -> dict[str, Any]:
    return {"kind": "spur_gear", "id": "gear", "name": "Gear", "module": 2, "teeth": 20, "face_width": 10} | over


def enclosure(**over: Any) -> dict[str, Any]:
    dims = {"width": 80, "depth": 60, "height": 30, "wall": 2, "floor": 2, "lid_thickness": 2, "lip_height": 4}
    return {"kind": "shell_with_lid", "id": "shell", "name": "Shell"} | dims | over


LID = {"kind": "lid", "id": "lid", "name": "Lid", "of": "box"}
PAD = {"kind": "extrude", "id": "pad", "name": "Pad", "sketch": "s", "distance": 5}
SQUARE = [{"id": "s", "entities": [{"kind": "rect", "width": 40, "height": 40}]}]


def messages(d: Design) -> list[str]:
    return [str(e) for e in validate(d)]


def test_flank_has_the_standard_proportions_and_thickness() -> None:
    m, z = 2.0, 20
    flank = gear_flank(m, z, 20, 0.0)
    radii = [math.hypot(x, y) for x, y in flank]
    assert (radii[0], radii[-1]) == pytest.approx((m * z / 2 - 1.25 * m, m * z / 2 + m))
    base = m * z / 2 * math.cos(math.radians(20))
    assert radii[1] == pytest.approx(base)
    half_at_base = math.atan2(-flank[1][1], flank[1][0])
    assert half_at_base == pytest.approx(math.pi / 2 / z + involute(math.radians(20)))


def test_gear_problems_catch_pointed_teeth_and_bad_counts() -> None:
    assert gear_problems(2, 20, 20, 0) == []
    assert any("whole number" in p for p in gear_problems(2, 20.5, 20, 0))
    assert any("point" in p for p in gear_problems(2, 20, 20, 3))


def test_din6885_rows_and_range() -> None:
    assert din6885(20) == (6, 3.5, 2.8)
    assert din6885(30) == (8, 4.0, 3.3)
    with pytest.raises(ValueError, match="6 up to 110"):
        din6885(5)


def test_screw_holes_follow_the_fastener_table() -> None:
    assert screw_holes("M3") == (3.0, 2.5, 3.4)


def test_valid_high_level_designs_compile_with_their_prelude_only_when_used() -> None:
    d = design(part("box", enclosure()), part("lid", LID))
    assert messages(d) == []
    source = compile_design(d)
    assert "def _enclosure(" in source and "tool = _lid(" in source and "MATES = [('lid_on_box', 'box', 'lid')]" in source
    plain = design(part("p", PAD, sketches=SQUARE))
    assert "_gear" not in compile_design(plain)
    assert Design.model_validate_json(d.model_dump_json()) == d


def test_lid_is_placed_by_an_implied_joint() -> None:
    d = design(part("box", enclosure()), part("lid", LID))
    joint, parent = joint_tree(d)["lid"]
    assert (joint.id, parent) == ("lid_on_box", "box")


@pytest.mark.parametrize(
    ("features", "expected"),
    [
        ([gear(teeth=20.5)], "spur_gear: teeth must be a whole number"),
        ([gear(bore=40)], "spur_gear: bore 40 must be smaller than the root diameter"),
        ([gear(hub_diameter=20)], "spur_gear: give both hub_diameter and hub_length"),
        ([gear(module=-1)], "features.gear.module: must be > 0"),
        (
            [{"kind": "rib", "id": "r", "name": "R", "plane": {}, "start": [0, 0], "end": [9, 0], "thickness": 2, "height": 5}],
            "rib: a rib needs an earlier feature",
        ),
        (
            [PAD, {"kind": "rib", "id": "r", "name": "R", "plane": {}, "start": [1, 1], "end": [1, 1], "thickness": 2, "height": 5}],
            "same point",
        ),
        (
            [
                PAD,
                {"kind": "boss_pattern", "id": "b", "name": "B", "plane": {}, "at": {"kind": "points", "points": [[0, 0]]}, "diameter": 4},
            ],
            "Field required",
        ),
        (
            [
                PAD,
                {
                    "kind": "boss_pattern",
                    "id": "b",
                    "name": "B",
                    "plane": {"ref": "pad.end"},
                    "at": {"kind": "points", "points": [[0, 0]]},
                    "diameter": 4,
                    "height": 5,
                    "hole_diameter": 5,
                },
            ],
            "boss_pattern: hole_diameter 5 must be smaller than the boss diameter 4",
        ),
        ([enclosure(lip_height=28)], "shell_with_lid: lip_height 28 must be less than the inside depth 28"),
        ([enclosure(wall=15)], "leave no opening"),
        ([enclosure(screw="M99")], "unknown screw 'M99'"),
        ([enclosure(boss_diameter=3)], "boss_diameter 3 must exceed"),
        ([PAD, {"kind": "keyway", "id": "k", "name": "K", "of": "nothing"}], "keyway: 'nothing' is not an earlier extrude"),
        ([PAD, {"kind": "groove", "id": "g", "name": "G", "of": "pad", "position": 1, "width": 1, "depth": 0}], "depth: must be > 0"),
    ],
)
def test_invalid_features_name_the_feature_and_problem(features: list[dict[str, Any]], expected: str) -> None:
    try:
        found = messages(design(part("p", *features, sketches=SQUARE)))
    except ValueError as e:
        found = [str(e)]
    assert any(expected in m for m in found), found


def test_lid_must_close_another_parts_shell() -> None:
    lonely = design(part("lid", {**LID, "of": "nowhere"}))
    assert any("lid: 'nowhere' is not another part with a shell_with_lid" in m for m in messages(lonely))
    twice = design(part("box", enclosure()), part("lid", LID), part("lid2", LID))
    assert any("already has a lid" in m for m in messages(twice))
