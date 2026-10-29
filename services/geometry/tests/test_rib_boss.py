import math
from pathlib import Path
from typing import Any

import pytest

from partwright_geometry import BuildError, LocalGeometry
from partwright_ir import Design, validate

W, D, H, T = 60.0, 40.0, 20.0, 2.0
TRAY = [
    {"kind": "extrude", "id": "tray", "name": "Tray", "sketch": "s", "distance": H},
    {"kind": "shell", "id": "hollow", "name": "Hollow", "thickness": T, "open": [{"normal": "+z"}]},
]
FLOOR = {"ref": "XY", "offset": T}


def tray(*features: dict[str, Any]) -> Design:
    part = {"id": "p", "name": "Tray", "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": W, "height": D}]}]}
    return Design.model_validate({"title": "Tray", "params": [], "parts": [part | {"features": [*TRAY, *features]}]})


def rib(start: list[float], end: list[float]) -> dict[str, Any]:
    return {"kind": "rib", "id": "rib", "name": "Rib", "plane": FLOOR, "start": start, "end": end, "thickness": 2, "height": 10}


BOSSES = {
    "kind": "boss_pattern",
    "id": "bosses",
    "name": "Bosses",
    "plane": FLOOR,
    "at": {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": 40, "spacing_y": 24},
    "diameter": 6,
    "height": 8,
    "hole_diameter": 2.5,
    "hole_depth": 6,
}
HOLLOW = W * D * H - (W - 2 * T) * (D - 2 * T) * (H - T)


def test_rib_runs_from_wall_to_wall_even_when_drawn_past_them(geometry: LocalGeometry, tmp_path: Path) -> None:
    exact, past = tray(rib([-W / 2 + T, 0], [W / 2 - T, 0])), tray(rib([-50, 0], [50, 0]))
    assert validate(exact) == [] and validate(past) == []
    volumes = [p.volume for d in (exact, past) for p in geometry.measure(d)]
    assert volumes == pytest.approx([HOLLOW + (W - 2 * T) * 2 * 10] * 2, rel=1e-9)


def test_a_rib_inside_material_is_an_error(geometry: LocalGeometry) -> None:
    with pytest.raises(BuildError, match="rib rib: the middle of its line is inside material"):
        geometry.measure(tray(rib([-W / 2 + 0.5, -10], [-W / 2 + 0.5, 10]) | {"plane": {"ref": "XY", "offset": 0}, "height": 1}))


def test_boss_pattern_volume_holes_and_positions(geometry: LocalGeometry) -> None:
    d = tray(BOSSES)
    assert validate(d) == []
    (part,) = geometry.measure(d)
    expected = HOLLOW + 4 * math.pi * 3**2 * 8 - 4 * math.pi * 1.25**2 * 6
    assert part.volume == pytest.approx(expected, rel=1e-9)
    assert [h.diameter for h in part.holes] == pytest.approx([2.5] * 4)
    assert sorted(h.center[:2] for h in part.holes) == pytest.approx(sorted((x, y) for x in (-20, 20) for y in (-12, 12)))
    assert part.bbox_size[2] == pytest.approx(H)


def test_floating_bosses_are_an_error(geometry: LocalGeometry) -> None:
    with pytest.raises(BuildError, match="boss_pattern bosses does not touch the part"):
        geometry.measure(tray(BOSSES | {"plane": {"ref": "XY", "offset": 30}}))
