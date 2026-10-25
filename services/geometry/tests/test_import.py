import math
from pathlib import Path
from typing import Any

import pytest
import trimesh

from partwright_geometry import Artifact, LocalGeometry
from partwright_ir import Design

PLATE_WITH_HOLES: dict[str, Any] = {
    "title": "Plate",
    "params": [],
    "parts": [
        {
            "id": "plate",
            "name": "Plate",
            "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": 80, "height": 60}]}],
            "features": [
                {"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": 5},
                {
                    "kind": "hole",
                    "id": "holes",
                    "name": "Holes",
                    "plane": {"offset": 5},
                    "at": {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": 60, "spacing_y": 40},
                    "diameter": 6.6,
                },
            ],
        }
    ],
}


@pytest.fixture(scope="module")
def plate(geometry: LocalGeometry, tmp_path_factory: pytest.TempPathFactory) -> Artifact:
    return geometry.build(Design.model_validate(PLATE_WITH_HOLES), tmp_path_factory.mktemp("plate"))


def test_step_descriptor_round_trip(geometry: LocalGeometry, plate: Artifact) -> None:
    d = geometry.describe(plate.files["step"])
    assert d.bbox_sorted == pytest.approx((5, 60, 80))
    assert d.volume == pytest.approx(plate.parts[0].volume, rel=1e-6)
    assert d.area == pytest.approx(2 * (80 * 60 - 4 * math.pi * 3.3**2) + 2 * 5 * (80 + 60) + 4 * math.pi * 6.6 * 5, rel=1e-6)
    assert d.hole_diameters == pytest.approx([6.6] * 4)
    assert d.face_kinds == {"plane": 6, "cylinder": 4}


@pytest.mark.parametrize("suffix", [".stl", ".obj"])
def test_mesh_descriptor_round_trip(geometry: LocalGeometry, plate: Artifact, suffix: str) -> None:
    path = plate.files["stl"].with_suffix(suffix)
    trimesh.load_mesh(plate.files["stl"]).export(path)
    d = geometry.describe(path)
    assert d.bbox_sorted == pytest.approx((5, 60, 80), abs=1e-3)
    assert d.volume == pytest.approx(plate.parts[0].volume, rel=1e-2)
    assert d.hole_diameters == [] and d.face_kinds["triangle"] > 12


def test_import_step_reuses_part_metrics(geometry: LocalGeometry, plate: Artifact) -> None:
    (part,) = geometry.import_step(plate.files["step"])
    assert part.name == "Plate" and part.valid and part.solids == 1
    assert part.holes == plate.parts[0].holes


def test_describe_rejects_unknown_format(geometry: LocalGeometry, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="expected one of"):
        geometry.describe(tmp_path / "part.igs")


def test_import_step_keeps_parts_and_names(geometry: LocalGeometry, tmp_path: Path) -> None:
    plate = PLATE_WITH_HOLES["parts"][0]
    lid = {
        **plate,
        "id": "lid",
        "name": "Lid",
        "sketches": [{**plate["sketches"][0], "plane": {"offset": 10}}],
        "features": plate["features"][:1],
    }
    art = geometry.build(Design.model_validate({**PLATE_WITH_HOLES, "parts": [plate, lid]}), tmp_path)
    parts = geometry.import_step(art.files["step"])
    assert [(p.name, len(p.holes)) for p in parts] == [("Plate", 4), ("Lid", 0)]
    assert [p.volume for p in parts] == pytest.approx([p.volume for p in art.parts], rel=1e-6)
