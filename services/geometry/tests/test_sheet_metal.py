import math
from pathlib import Path
from typing import Any

import pytest

from scriber_geometry import BuildError, LocalGeometry
from scriber_ir import Design, validate


def strap(bends: list[dict[str, Any]], before: tuple[dict[str, Any], ...] = ()) -> Design:
    flat = [
        {"kind": "rect", "center": [0, 20], "width": 100, "height": 80},
        {"kind": "circle", "center": [0, 50], "diameter": 8, "subtract": True},
    ]
    sheet = {"kind": "sheet_metal", "id": "sheet", "name": "Sheet", "sketch": "flat", "thickness": 2, "bend_radius": 2, "bends": bends}
    part = {
        "id": "p",
        "name": "Strap",
        "process": "sheet_metal",
        "sketches": [{"id": "flat", "entities": flat}],
        "features": [*before, sheet],
    }
    return Design.model_validate({"title": "Strap", "params": [], "parts": [part]})


@pytest.mark.parametrize(("direction", "z_min"), [("up", 0.0), ("down", -29.91)])
def test_a_bend_folds_the_far_panel_with_the_bend_allowance(direction: str, z_min: float, geometry: LocalGeometry, tmp_path: Path) -> None:
    design = strap([{"line": [[-50, 30], [50, 30]], "direction": direction}])
    assert validate(design) == []
    part = geometry.build(design, tmp_path).parts[0]
    allowance = math.pi / 2 * (2 + 0.33 * 2)
    flange = 60 - 30 - allowance / 2
    assert part.valid and part.solids == 1
    assert part.bbox_size == pytest.approx((100, 50 - allowance / 2 + 4, flange + 4), abs=0.01)
    assert part.bbox_min[2] == pytest.approx(z_min, abs=0.01)
    assert [h.axis for h in part.holes] == [pytest.approx((0, 1, 0), abs=1e-6)]


def test_two_bends_make_a_channel(geometry: LocalGeometry, tmp_path: Path) -> None:
    part = geometry.build(strap([{"line": [[-50, 30], [50, 30]]}, {"line": [[-50, -10], [50, -10]]}]), tmp_path).parts[0]
    assert part.valid and part.solids == 1 and part.bbox_size[2] == pytest.approx(31.91, abs=0.01)


def test_sheet_metal_must_come_first() -> None:
    pad = {"kind": "extrude", "id": "pad", "name": "Pad", "sketch": "flat", "distance": 2}
    assert any("must be the first feature" in e.message for e in validate(strap([], (pad,))))


def plate(bends: list[dict[str, Any]], flanges: list[dict[str, Any]], cuts: list[dict[str, Any]]) -> Design:
    flat = [{"kind": "rect", "width": 100, "height": 60}, *cuts]
    sheet = {"kind": "sheet_metal", "id": "sheet", "name": "Sheet", "sketch": "flat", "thickness": 2, "bend_radius": 2}
    sheet |= {"bends": bends, "flanges": flanges}
    part = {"id": "p", "name": "Plate", "sketches": [{"id": "flat", "entities": flat}], "features": [sheet]}
    return Design.model_validate({"title": "Plate", "params": [], "parts": [part]})


def test_flanges_and_a_hem_grow_the_flat_and_export_it(geometry: LocalGeometry, tmp_path: Path) -> None:
    up = {"edge": [[-50, 30], [50, 30]], "length": 20}
    hem = {"edge": [[50, -30], [50, 30]], "length": 8, "angle": 180, "radius": 0.5}
    art = geometry.build(plate([], [up, hem], []), tmp_path)
    assert art.parts[0].solids == 1 and art.parts[0].bbox_size == pytest.approx((102.5, 64, 24), abs=0.01)
    dxf = art.files["dxf"].read_text()
    assert "bends" in dxf and "outline" in dxf


def test_a_tab_bends_inside_its_cut_and_a_bend_that_splits_nothing_fails(geometry: LocalGeometry, tmp_path: Path) -> None:
    cut = [
        {"kind": "rect", "center": c, "width": w, "height": h, "subtract": True}
        for c, w, h in (([0, 10], 24, 2), ([-11, 0], 2, 20), ([11, 0], 2, 20))
    ]
    tab = geometry.build(plate([{"line": [[-10, -10], [10, -10]], "relief": 2}], [], cut), tmp_path / "tab").parts[0]
    assert tab.bbox_size == pytest.approx((100, 60, 20.91), abs=0.01)
    with pytest.raises(BuildError, match="does not split the flat"):
        geometry.build(plate([{"line": [[-10, -10], [10, -10]]}], [], []), tmp_path / "solid")
