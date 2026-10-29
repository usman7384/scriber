import math
from pathlib import Path
from typing import Any

import pytest
import trimesh

from partwright_geometry import LocalGeometry, hausdorff, reconstruct_mesh
from partwright_ir import Design, apply_params, validate

STEPPED: dict[str, Any] = {
    "title": "Stepped plate",
    "params": [],
    "parts": [
        {
            "id": "plate",
            "name": "Plate",
            "sketches": [
                {"id": "s", "entities": [{"kind": "rect", "width": 80, "height": 60}]},
                {"id": "boss", "plane": {"offset": 6}, "entities": [{"kind": "circle", "center": [10, 0], "diameter": 30}]},
                {"id": "slot", "entities": [{"kind": "slot", "center": [-25, 0], "length": 20, "width": 8, "angle": 90}]},
            ],
            "features": [
                {"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": 6},
                {"kind": "extrude", "id": "boss", "name": "Boss", "sketch": "boss", "distance": 10},
                {"kind": "extrude", "id": "slot", "name": "Slot", "sketch": "slot", "mode": "cut", "extent": "through_all"},
                {
                    "kind": "hole",
                    "id": "holes",
                    "name": "Holes",
                    "plane": {"offset": 6},
                    "at": {"kind": "points", "points": [[30, 20], [30, -20], [-30, 20]]},
                    "diameter": 5,
                },
                {
                    "kind": "hole",
                    "id": "pocket",
                    "name": "Pocket",
                    "plane": {"offset": 16},
                    "at": {"kind": "points", "points": [[10, 0]]},
                    "diameter": 12,
                    "depth": 4,
                },
            ],
        }
    ],
}


@pytest.fixture(scope="module")
def stepped(geometry: LocalGeometry, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return geometry.build(Design.model_validate(STEPPED), tmp_path_factory.mktemp("stepped")).files["stl"]


def test_stepped_plate_comes_back_as_a_named_feature_tree(geometry: LocalGeometry, stepped: Path, tmp_path: Path) -> None:
    design = reconstruct_mesh(stepped)
    assert validate(design) == []
    features = {f.id: f.kind for f in design.parts[0].features}
    assert features == {"body": "extrude", "boss_1": "extrude", "holes": "hole", "bore": "extrude", "window": "extrude"}
    values = design.param_values()
    assert (values["thickness"], values["boss_1_height"], values["boss_1_diameter"]) == pytest.approx((6, 10, 30), abs=1e-3)
    assert (values["hole_diameter"], values["bore_diameter"]) == pytest.approx((5, 12), abs=1e-3)
    assert all(p.provenance.source == "mesh_fit" for p in design.params)
    art = geometry.build(design, tmp_path)
    assert art.ok and art.parts[0].valid and art.parts[0].solids == 1
    assert hausdorff(stepped, art.files["stl"]) < 0.05


def test_editing_a_fitted_height_moves_the_features_above_it(geometry: LocalGeometry, stepped: Path, tmp_path: Path) -> None:
    design = apply_params(reconstruct_mesh(stepped), {"thickness": 9})
    (part,) = geometry.build(design, tmp_path).parts
    assert part.valid and part.bbox_size[2] == pytest.approx(19, abs=1e-6)


def test_meshes_that_are_open_or_have_no_z_planes_fail_fast(tmp_path: Path) -> None:
    open_box = trimesh.creation.box(extents=(10, 10, 10))
    open_box.update_faces(list(range(len(open_box.faces) - 1)))
    open_box.export(tmp_path / "open.stl")
    with pytest.raises(ValueError, match="watertight"):
        reconstruct_mesh(tmp_path / "open.stl")
    tilted = trimesh.creation.box(extents=(10, 10, 10))
    tilted.apply_transform(trimesh.transformations.rotation_matrix(math.radians(40), (1, 1, 0)))
    tilted.export(tmp_path / "tilted.stl")
    with pytest.raises(ValueError, match="normal to Z"):
        reconstruct_mesh(tmp_path / "tilted.stl")
