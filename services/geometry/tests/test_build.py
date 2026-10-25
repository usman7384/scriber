from pathlib import Path
from typing import Any

import pytest
import trimesh
from build123d import import_step

from partwright_geometry import BuildError, LocalGeometry
from partwright_ir import Design, apply_params

BRACKET: dict[str, Any] = {
    "title": "Mounting bracket",
    "params": [
        {"name": "length", "value": 80, "unit": "mm"},
        {"name": "width", "value": 60, "unit": "mm"},
        {"name": "thickness", "value": 5, "unit": "mm"},
        {"name": "spacing_x", "value": 60, "unit": "mm"},
    ],
    "parts": [
        {
            "id": "bracket",
            "name": "Bracket",
            "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "length", "height": "width"}]}],
            "features": [
                {"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "s", "distance": "thickness"},
                {
                    "kind": "hole",
                    "id": "holes",
                    "name": "Holes",
                    "plane": {"offset": "thickness"},
                    "at": {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "spacing_x", "spacing_y": 40},
                    "diameter": 6.6,
                },
                {"kind": "fillet", "id": "corners", "name": "Corner fillets", "edges": "parallel_z", "radius": 4},
            ],
        }
    ],
}

TUBE: dict[str, Any] = {
    "title": "Hollow cylinder",
    "params": [{"name": "od", "value": 24, "unit": "mm"}, {"name": "wall", "value": 2, "unit": "mm"}],
    "parts": [
        {
            "id": "tube",
            "name": "Tube",
            "sketches": [
                {
                    "id": "ring",
                    "entities": [{"kind": "circle", "diameter": "od"}, {"kind": "circle", "diameter": "od - 2 * wall", "subtract": True}],
                }
            ],
            "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "ring", "distance": 50}],
        }
    ],
}


def variant(base: dict[str, Any], **part: Any) -> Design:
    return Design.model_validate({**base, "parts": [{**base["parts"][0], **part}]})


def test_bracket_builds_valid_solid_with_holes(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(Design.model_validate(BRACKET), tmp_path)
    assert art.ok, art.findings
    (part,) = art.parts
    assert part.solids == 1 and part.valid
    assert part.bbox_size == pytest.approx((80, 60, 5), abs=1e-6)
    assert [round(h.diameter, 3) for h in part.holes] == [6.6] * 4
    assert sorted({round(h.center[0], 3) for h in part.holes}) == [-30, 30]


def test_exports_reload(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(Design.model_validate(BRACKET), tmp_path)
    assert import_step(art.files["step"]).volume == pytest.approx(art.parts[0].volume, rel=1e-6)
    assert trimesh.load_mesh(art.files["stl"]).is_watertight
    assert art.files["glb"].read_bytes()[:4] == b"glTF"
    assert "def build():" in art.files["py"].read_text()


def test_param_edit_moves_holes(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(apply_params(Design.model_validate(BRACKET), {"spacing_x": 70}), tmp_path)
    assert sorted({round(h.center[0], 3) for h in art.parts[0].holes}) == [-35, 35]


def test_tube_bore_is_detected_as_hole(geometry: LocalGeometry, tmp_path: Path) -> None:
    (part,) = geometry.build(Design.model_validate(TUBE), tmp_path).parts
    assert [round(h.diameter, 3) for h in part.holes] == [20]
    assert part.holes[0].length == pytest.approx(50)


def test_floating_feature_is_reported(geometry: LocalGeometry, tmp_path: Path) -> None:
    two_discs = [{"id": "ring", "entities": [{"kind": "circle", "diameter": 10}, {"kind": "circle", "center": [50, 0], "diameter": 10}]}]
    art = geometry.build(variant(TUBE, sketches=two_discs), tmp_path)
    assert any(f.rule_id == "GEO-ONE-SOLID" for f in art.findings)


def test_kernel_failure_raises_build_error(geometry: LocalGeometry, tmp_path: Path) -> None:
    huge_fillet = {"kind": "fillet", "id": "f", "name": "F", "edges": "all", "radius": 40}
    with pytest.raises(BuildError) as e:
        geometry.build(variant(BRACKET, features=[*BRACKET["parts"][0]["features"][:2], huge_fillet]), tmp_path)
    assert e.value.kind == "kernel"


def test_timeout_kills_worker_and_next_build_recovers(geometry: LocalGeometry, tmp_path: Path) -> None:
    assert geometry.build(Design.model_validate(TUBE), tmp_path).ok
    geometry.timeout_s = 2
    try:
        with pytest.raises(BuildError) as e:
            geometry._call({"op": "build", "rules": {}, "source": "while True: pass", "out_dir": str(tmp_path), "title": "x"})
        assert e.value.kind == "timeout"
    finally:
        geometry.timeout_s = 120
    assert geometry.build(Design.model_validate(TUBE), tmp_path).ok


def test_hole_that_misses_the_part_names_the_feature(geometry: LocalGeometry, tmp_path: Path) -> None:
    features = BRACKET["parts"][0]["features"]
    missing = {**features[1], "plane": {"offset": 0}, "depth": 3}
    with pytest.raises(BuildError) as e:
        geometry.build(variant(BRACKET, features=[features[0], missing]), tmp_path)
    assert e.value.feature == "holes"
    assert "removed no material" in str(e.value)


def test_hole_on_the_edge_is_rejected(geometry: LocalGeometry, tmp_path: Path) -> None:
    features = BRACKET["parts"][0]["features"]
    edge = {**features[1], "at": {"kind": "points", "points": [[0, 30]]}}
    with pytest.raises(BuildError) as e:
        geometry.build(variant(BRACKET, features=[features[0], edge]), tmp_path)
    assert e.value.feature == "holes"
    assert "lies outside the part: its centre Y must be between -26.7 and 26.7" in str(e.value)


def test_vertical_fillet_skips_hole_seams(geometry: LocalGeometry, tmp_path: Path) -> None:
    features = BRACKET["parts"][0]["features"]
    art = geometry.build(variant(BRACKET, features=[*features[:2], {**features[2], "radius": 3}]), tmp_path)
    assert art.ok
    assert len(art.parts[0].holes) == 4
