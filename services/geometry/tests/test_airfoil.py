import math
from collections.abc import Sequence
from pathlib import Path

import pytest

from partwright_geometry import BuildError, LocalGeometry
from partwright_ir import Design, validate

TIP_LE = ["wing_span / 2 * tan(sweep)", "wing_span / 2 * tan(dihedral)"]


def section(sid: str, offset: str | float, chord: str, le: Sequence[str | float], twist: str | float) -> dict[str, object]:
    plane = {"ref": "XZ", "offset": offset}
    return {
        "kind": "airfoil_section",
        "id": sid,
        "name": sid,
        "plane": plane,
        "naca": "2412",
        "chord": chord,
        "leading_edge": le,
        "twist": twist,
    }


WING = Design.model_validate(
    {
        "title": "Wing",
        "params": [
            {"name": "wing_span", "value": 1000, "unit": "mm"},
            {"name": "root_chord", "value": 250, "unit": "mm"},
            {"name": "tip_chord", "value": 120, "unit": "mm"},
            {"name": "sweep", "value": 20, "unit": "deg"},
            {"name": "dihedral", "value": 5, "unit": "deg"},
            {"name": "twist", "value": 2, "unit": "deg"},
        ],
        "parts": [
            {
                "id": "wing",
                "name": "Wing",
                "sketches": [],
                "features": [
                    section("root_airfoil", 0, "root_chord", [0, 0], 0),
                    section("tip_airfoil", "wing_span / 2", "tip_chord", TIP_LE, "-twist"),
                    {"kind": "loft", "id": "main_wing", "name": "main_wing", "sections": ["root_airfoil", "tip_airfoil"], "ruled": True},
                    {
                        "kind": "pattern",
                        "id": "full_wing",
                        "name": "full_wing",
                        "features": ["main_wing"],
                        "type": "mirror",
                        "mirror_plane": "XZ",
                    },
                ],
            }
        ],
    }
)


def test_mirrored_wing_is_one_valid_solid_with_the_given_span(geometry: LocalGeometry, tmp_path: Path) -> None:
    assert validate(WING) == []
    (part,) = geometry.build(WING, tmp_path).parts
    assert (part.solids, part.valid) == (1, True)
    assert part.bbox_size[1] == pytest.approx(1000, abs=1e-6)


def test_tip_section_is_swept_raised_and_washed_out(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(WING, tmp_path)
    root, tip = geometry.sections(art.files["step"], [0.0, -500.0])
    le = min(tip, key=lambda p: p[0])
    te = max(tip, key=lambda p: p[0])
    assert {round(p[1], 6) for p in tip} == {-500.0}
    assert le[0] == pytest.approx(500 * math.tan(math.radians(20)), abs=0.2)
    assert le[2] == pytest.approx(500 * math.tan(math.radians(5)), abs=0.5)
    assert te[2] > le[2]
    assert max(p[0] for p in root) == pytest.approx(250, abs=0.1)


def test_section_outside_the_part_is_an_error(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(WING, tmp_path)
    with pytest.raises(BuildError, match="no material at y = 900"):
        geometry.sections(art.files["step"], [900.0])
