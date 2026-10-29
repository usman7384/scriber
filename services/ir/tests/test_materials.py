import pytest

from partwright_ir import material


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("Aluminum 6061", "Aluminum 6061-T6"),
        ("aluminium 7075-T6", "Aluminum 7075-T6"),
        ("AISI 304 stainless", "Stainless steel 1.4301"),
        ("S235JR", None),
        ("S235 steel", "Structural steel S235"),
        ("PLA+", "PLA"),
        ("brass", None),
    ],
)
def test_lookup_prefers_the_grade_over_the_family(text: str, name: str | None) -> None:
    found = material(text)
    assert (found.name if found else None) == name


def test_every_material_cites_a_source() -> None:
    found = material("Aluminum 6061")
    assert found is not None and (found.density_g_cm3, found.youngs_modulus_gpa) == (2.70, 68.9) and "MA6061T6" in found.source
