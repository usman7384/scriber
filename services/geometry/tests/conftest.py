from collections.abc import Iterator
from typing import Any

import pytest

from partwright_geometry import LocalGeometry


@pytest.fixture(scope="session")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()


@pytest.fixture
def plate() -> dict[str, Any]:
    return {
        "title": "Plate with boss",
        "params": [{"name": "boss_height", "value": 10, "unit": "mm"}],
        "parts": [
            {
                "id": "plate",
                "name": "Plate",
                "material": "steel",
                "sketches": [
                    {"id": "s", "entities": [{"kind": "rect", "width": 40, "height": 30}]},
                    {"id": "b", "plane": {"ref": "base.end"}, "entities": [{"kind": "circle", "diameter": 10}]},
                ],
                "features": [
                    {"kind": "extrude", "id": "base", "name": "Base", "sketch": "s", "distance": 5},
                    {"kind": "extrude", "id": "boss", "name": "Boss", "sketch": "b", "distance": "boss_height"},
                ],
                "face_groups": [
                    {"name": "mount_face", "faces": {"normal": "-z"}},
                    {"name": "load_face", "faces": {"of": "boss", "normal": "+z", "extreme": "max"}},
                ],
            }
        ],
    }
