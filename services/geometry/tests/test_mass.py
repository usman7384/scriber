import math
from pathlib import Path
from typing import Any

import pytest

from partwright_geometry import LocalGeometry, assembly_mass, density
from partwright_ir import Design

BASE_AND_PUCK: dict[str, Any] = {
    "title": "Base and puck",
    "params": [],
    "parts": [
        {
            "id": "base",
            "name": "Base",
            "material": "Steel S235",
            "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": 40, "height": 40}]}],
            "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": 10}],
        },
        {
            "id": "puck",
            "name": "Puck",
            "material": "PLA",
            "sketches": [{"id": "s", "plane": {"offset": 10}, "entities": [{"kind": "circle", "center": [10, 0], "diameter": 20}]}],
            "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": 10}],
        },
    ],
}


def test_assembly_mass_matches_hand_calculation(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(Design.model_validate(BASE_AND_PUCK), tmp_path)
    base_g, puck_g = 40 * 40 * 10 * 7.85 / 1000, math.pi * 10**2 * 10 * 1.24 / 1000
    assert [p.mass_g for p in art.parts] == pytest.approx([base_g, puck_g], rel=1e-6)
    mass, cog = assembly_mass(art.parts)
    expected = (puck_g * 10 / (base_g + puck_g), 0, (base_g * 5 + puck_g * 15) / (base_g + puck_g))
    assert mass == pytest.approx(base_g + puck_g, rel=1e-6)
    assert cog == pytest.approx(expected, abs=1e-6)


def test_unknown_material_has_no_mass(geometry: LocalGeometry, tmp_path: Path) -> None:
    parts = [{**p, "material": "unobtainium"} for p in BASE_AND_PUCK["parts"]]
    art = geometry.build(Design.model_validate({**BASE_AND_PUCK, "parts": parts}), tmp_path)
    assert [p.mass_g for p in art.parts] == [None, None]
    assert art.parts[0].center_of_mass == pytest.approx((0, 0, 5))
    with pytest.raises(ValueError, match="no mass"):
        assembly_mass(art.parts)


@pytest.mark.parametrize(
    ("material", "rho"),
    [
        ("Al 6061-T6", 2.70),
        ("stainless steel 1.4301", 7.9),
        ("S235 steel", 7.85),
        ("PETG", 1.27),
        ("PLA+", 1.24),
        ("ABS", 1.04),
        ("PA12", 1.01),
        ("brass", None),
    ],
)
def test_density_table(material: str, rho: float | None) -> None:
    assert density(material) == rho
