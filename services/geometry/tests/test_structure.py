import pytest

from scriber_geometry import LocalGeometry
from scriber_ir import Design

PLATE = Design.model_validate(
    {
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
                    {"kind": "fillet", "id": "corners", "name": "Corner fillets", "edges": "parallel_z", "radius": 4},
                ],
            }
        ],
    }
)


def test_every_face_belongs_to_the_feature_that_made_it(geometry: LocalGeometry) -> None:
    plate = geometry.structure(PLATE)["plate"]
    owned = {fid: len(faces) for fid, faces in plate.features.items()}
    assert owned == {"body": 6, "holes": 4, "corners": 4}
    assert sorted(i for faces in plate.features.values() for i in faces) == list(range(len(plate.faces)))
    for face in plate.faces:
        assert face.indices and len(face.indices) % 3 == 0 and max(face.indices) < len(face.positions) // 3
    assert plate.placement == pytest.approx([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0])


def block(pid: str, size: float) -> dict[str, object]:
    sketch = {"id": "s", "entities": [{"kind": "rect", "width": size, "height": size}]}
    return {
        "id": pid,
        "name": pid,
        "sketches": [sketch],
        "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": size}],
    }


STACK = Design.model_validate(
    {
        "title": "Stack",
        "params": [],
        "parts": [block("plate", 40), block("cube", 10)],
        "assembly": {
            "connectors": [
                {"id": "seat", "part": "plate", "origin": [10, 0, 40], "z": "+z", "x": "+y"},
                {"id": "foot", "part": "cube", "origin": [0, 0, 0]},
            ],
            "joints": [{"id": "cube_on_plate", "parent": "seat", "child": "foot", "angle": 90}],
        },
    }
)


def test_assembly_faces_are_placed_where_the_part_sits(geometry: LocalGeometry) -> None:
    cube = geometry.structure(STACK)["cube"]
    assert cube.placement[:4] == pytest.approx([-1, 0, 0, 10], abs=1e-12)
    zs = [z for face in cube.faces for z in face.positions[2::3]]
    assert min(zs) == pytest.approx(40) and max(zs) == pytest.approx(50)
