from pathlib import Path
from typing import Any

import pytest

from scriber_geometry import BuildError, LocalGeometry
from scriber_ir import Design, validate


def part(sketches: list[dict[str, Any]], features: list[dict[str, Any]]) -> Design:
    return Design.model_validate(
        {"title": "t", "params": [], "parts": [{"id": "p", "name": "P", "sketches": sketches, "features": features}]}
    )


def square(sid: str, size: float, plane: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"id": sid, "plane": plane or {"ref": "XY"}, "entities": [{"kind": "rect", "width": size, "height": size}]}


def extrude(fid: str, sketch: str, distance: float, mode: str = "add") -> dict[str, Any]:
    return {"kind": "extrude", "id": fid, "name": fid, "sketch": sketch, "distance": distance, "mode": mode}


def test_a_clockwise_polygon_extrudes_the_way_a_counter_clockwise_one_does(geometry: LocalGeometry, tmp_path: Path) -> None:
    sizes = []
    for points in ([[0, 0], [10, 0], [10, 10], [0, 10]], [[0, 0], [0, 10], [10, 10], [10, 0]]):
        boss = {"id": "boss", "plane": {"ref": "plate.top"}, "entities": [{"kind": "polygon", "points": points}]}
        design = part([square("plate", 40), boss], [extrude("plate", "plate", 10), extrude("lump", "boss", 10)])
        sizes.append(geometry.build(design, tmp_path / str(len(sizes))).parts[0].bbox_size)
    assert sizes == [(40, 40, 20), (40, 40, 20)]


def test_through_next_stops_past_the_first_wall(geometry: LocalGeometry, tmp_path: Path) -> None:
    sketches = [square("base", 60), square("column", 20), square("top", 60, {"ref": "XY", "offset": 40})]
    hole = {"kind": "hole", "id": "h", "name": "H", "plane": {"ref": "flange.top"}, "diameter": 8, "through": "next"}
    hole["at"] = {"kind": "points", "points": [[22, 22]]}
    features = [extrude("base", "base", 10), extrude("column", "column", 50), extrude("flange", "top", 10), hole]
    holes = geometry.build(part(sketches, features), tmp_path).parts[0].holes
    assert [(h.diameter, h.length) for h in holes] == [pytest.approx((8, 10))]


def test_an_arc_by_its_centre_sweeps_past_half_a_turn(geometry: LocalGeometry, tmp_path: Path) -> None:
    segments = [{"to": [10, 0]}, {"to": [-10, 0], "arc": "ccw", "center": [0, 10]}]
    sketch = {"id": "d", "entities": [{"kind": "path", "start": [-10, 0], "segments": segments}]}
    design = part([sketch], [extrude("body", "d", 5)])
    assert validate(design) == []
    assert geometry.build(design, tmp_path).parts[0].bbox_size == pytest.approx((28.284, 24.142, 5), abs=1e-3)
    off = [{"to": [10, 0]}, {"to": [-10, 0], "arc": "ccw", "center": [3, 10]}]
    bad = part([{"id": "d", "entities": [{"kind": "path", "start": [-10, 0], "segments": off}]}], [extrude("body", "d", 5)])
    assert any("from its center" in e.message for e in validate(bad))


def test_a_floating_feature_is_named(geometry: LocalGeometry, tmp_path: Path) -> None:
    design = part(
        [square("base", 40), square("high", 10, {"ref": "XY", "offset": 30})], [extrude("base", "base", 5), extrude("floater", "high", 5)]
    )
    found = [f.message for f in geometry.build(design, tmp_path).findings if f.rule_id == "GEO-ONE-SOLID"]
    assert "feature 'floater' adds a body that does not touch the rest of the part" in found


def test_the_outline_selector_takes_only_the_rim(geometry: LocalGeometry, tmp_path: Path) -> None:
    disc = {"id": "disc", "entities": [{"kind": "circle", "diameter": 100}, {"kind": "circle", "diameter": 20, "subtract": True}]}
    chamfer = {"kind": "chamfer", "id": "c", "name": "C", "edges": {"normal": "+z", "extreme": "max", "outline": True}, "length": 1}
    art = geometry.build(part([disc], [extrude("disc", "disc", 10), chamfer]), tmp_path)
    assert art.findings == [] and art.parts[0].bbox_size == pytest.approx((100, 100, 10))
    assert [h.diameter for h in art.parts[0].holes] == [pytest.approx(20)]


def test_threads_are_recorded_named_in_the_step_and_checked_against_the_shaft(geometry: LocalGeometry, tmp_path: Path) -> None:
    def shafted(diameter: float, modelled: bool) -> Design:
        shaft = {"id": "s", "plane": {"ref": "flange.top"}, "entities": [{"kind": "circle", "diameter": diameter}]}
        flange = {"id": "f", "entities": [{"kind": "circle", "diameter": 40}]}
        thread = {"kind": "thread", "id": "th", "name": "T", "of": "shaft", "designation": "M20x2.5", "position": 15, "modelled": modelled}
        tap = {"kind": "hole", "id": "tap", "name": "Tap", "plane": {"ref": "shaft.top"}, "type": "tapped", "fastener": "M8", "depth": 16}
        tap |= {"thread_depth": 12, "at": {"kind": "points", "points": [[0, 0]]}}
        return part([flange, shaft], [extrude("flange", "f", 10), extrude("shaft", "s", 30), thread, tap])

    assert validate(shafted(20, False)) == []
    with pytest.raises(BuildError, match="needs its major diameter, 20 mm"):
        geometry.build(shafted(18, False), tmp_path / "thin")
    cosmetic, modelled = (geometry.build(shafted(20, m), tmp_path / str(m)) for m in (False, True))
    assert [(t.designation, t.on, t.length) for t in cosmetic.parts[0].threads] == [("M20x2.5", "shaft", 15), ("M8x1.25", "bore", 12)]
    assert "thread_1_M20x2_5" in cosmetic.files["step"].read_text(errors="ignore")
    assert modelled.parts[0].valid and modelled.parts[0].volume < cosmetic.parts[0].volume - 100


@pytest.mark.parametrize(("mode", "change"), [("cut", -2280.0), ("add", 2520.0)])
def test_a_wrapped_pocket_keeps_its_size_on_the_surface_and_a_radial_depth(
    mode: str, change: float, geometry: LocalGeometry, tmp_path: Path
) -> None:
    window = {
        "id": "w",
        "plane": {"ref": "XZ", "offset": -30},
        "entities": [{"kind": "rect", "width": 20, "height": 40, "center": [0, 50]}],
    }
    shaft = {"id": "c", "entities": [{"kind": "circle", "diameter": 60}]}
    pocket = extrude("pocket", "w", 3, mode) | {"wrap": "shaft"}
    design = part([shaft, window], [extrude("shaft", "c", 100), pocket])
    assert validate(design) == []
    volume = geometry.build(design, tmp_path).parts[0].volume
    # a 20 mm arc on a 30 mm radius is 2/3 rad; 3 mm deep (or proud) over 40 mm of length
    assert volume - 3.14159265358979 * 900 * 100 == pytest.approx(change, abs=0.5)
