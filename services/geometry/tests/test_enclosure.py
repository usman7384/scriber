from pathlib import Path
from typing import Any

import pytest

from partwright_geometry import LocalGeometry
from partwright_ir import Design, validate

W, D, WALL, FLOOR, LID_T, LIP, GAP = 80.0, 60.0, 2.0, 2.0, 2.0, 4.0, 0.2


def enclosure(height: float, screw: str | None) -> Design:
    shell = {
        "kind": "shell_with_lid",
        "id": "shell",
        "name": "Shell",
        "width": W,
        "depth": D,
        "height": "h",
        "wall": WALL,
        "floor": FLOOR,
        "lid_thickness": LID_T,
        "lip_height": LIP,
        "clearance": GAP,
        "screw": screw,
    }
    lid = {"kind": "lid", "id": "lid", "name": "Lid", "of": "box"}
    parts: list[dict[str, Any]] = [
        {"id": "box", "name": "Box", "sketches": [], "features": [shell]},
        {"id": "lid", "name": "Lid", "sketches": [], "features": [lid]},
    ]
    return Design.model_validate({"title": "Enclosure", "params": [{"name": "h", "value": height, "unit": "mm"}], "parts": parts})


@pytest.mark.parametrize("height", [30.0, 45.0])
def test_box_and_lid_volumes_and_the_lid_sits_on_the_rim(geometry: LocalGeometry, tmp_path: Path, height: float) -> None:
    d = enclosure(height, None)
    assert validate(d) == []
    art = geometry.build(d, tmp_path)
    box, lid = art.parts
    assert box.volume == pytest.approx(W * D * height - (W - 2 * WALL) * (D - 2 * WALL) * (height - FLOOR), rel=1e-9)
    iw, idp = W - 2 * WALL - 2 * GAP, D - 2 * WALL - 2 * GAP
    assert lid.volume == pytest.approx(W * D * LID_T + (iw * idp - (iw - 2 * WALL) * (idp - 2 * WALL)) * LIP, rel=1e-9)
    assert lid.bbox_min[2] == pytest.approx(height - LIP) and lid.bbox_size[2] == pytest.approx(LID_T + LIP)
    assert art.assembly is not None and art.assembly.overlaps() == [] and art.assembly.broken_mates() == []
    assert art.assembly.mates[0].joint == "lid_on_box"


def test_corner_bosses_take_screws_through_the_lid(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(enclosure(30, "M3"), tmp_path)
    box, lid = art.parts
    x, y = (W - WALL - 7.5) / 2, (D - WALL - 7.5) / 2
    corners = sorted((sx * x, sy * y) for sx in (-1, 1) for sy in (-1, 1))
    assert [h.diameter for h in box.holes] == pytest.approx([2.5] * 4)
    assert sorted(h.center[:2] for h in box.holes) == pytest.approx(corners)
    assert [h.diameter for h in lid.holes] == pytest.approx([3.4] * 4)
    assert sorted(h.center[:2] for h in lid.holes) == pytest.approx(corners)
    assert art.assembly is not None and art.assembly.overlaps() == [] and art.assembly.broken_mates() == []
