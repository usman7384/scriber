import math
from pathlib import Path
from typing import Any

import pytest

from partwright_geometry import BuildError, LocalGeometry
from partwright_ir import Design

PLATE: dict[str, Any] = {
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


def test_face_groups_and_material_round_trip_through_step(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(Design.model_validate(PLATE), tmp_path)
    meta = geometry.step_metadata(art.files["step"])
    (body,) = meta.bodies
    groups = {g.name: g for g in body.face_groups}
    assert meta.schema_name.startswith("AP242")
    assert (body.name, body.material, body.density_g_cm3) == ("Plate", "steel", 7.85)
    assert groups["mount_face"].normal == (0.0, 0.0, -1.0)
    assert groups["mount_face"].area == pytest.approx(40 * 30)
    assert groups["load_face"].area == pytest.approx(math.pi * 25)
    assert groups["load_face"].center == pytest.approx((0, 0, 15))


def test_a_face_in_two_groups_is_rejected(geometry: LocalGeometry, tmp_path: Path) -> None:
    data = PLATE | {"parts": [PLATE["parts"][0] | {"face_groups": [{"name": n, "faces": {"normal": "-z"}} for n in ("a", "b")]}]}
    with pytest.raises(BuildError, match="in both 'a' and 'b'"):
        geometry.build(Design.model_validate(data), tmp_path)


def test_designs_without_metadata_keep_the_plain_export(geometry: LocalGeometry, tmp_path: Path) -> None:
    data = PLATE | {"parts": [PLATE["parts"][0] | {"material": None, "face_groups": []}]}
    art = geometry.build(Design.model_validate(data), tmp_path)
    (body,) = geometry.step_metadata(art.files["step"]).bodies
    assert (body.material, body.face_groups) == (None, [])
