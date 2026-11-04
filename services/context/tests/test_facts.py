import pytest

from scriber_context.facts import line_facts
from scriber_context.models import Fact
from scriber_context.parsed import Line
from scriber_context.quantities import normalise, quantities


def facts(text: str, page: int = 1, number: int = 1) -> list[Fact]:
    return line_facts("d0", Line(page, number, text))


def summary(text: str) -> list[tuple[str, str, float | str, str]]:
    return [(f.kind, f.name, f.value, f.unit) for f in facts(text)]


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [(0.25, "in", (6.35, "mm")), (2, "cm", (20, "mm")), (45, "°", (45, "deg")), (2, "kN", (2000, "N")), (500, "g", (0.5, "kg"))],
)
def test_units_normalise_to_mm_deg_and_si(value: float, unit: str, expected: tuple[float, str]) -> None:
    assert normalise(value, unit) == expected


def test_quantities_accept_decimal_commas_and_inch_marks() -> None:
    assert quantities('25,4 mm and 1" stock, 10 min') == [(25.4, "mm"), (25.4, "mm")]


def test_symmetric_diameter_tolerance_is_one_typed_fact() -> None:
    [fact] = facts("bore Ø82 ±0.2 mm", page=2, number=7)
    assert (fact.kind, fact.name, fact.value, fact.unit, fact.tol) == ("tolerance", "bore", 82.0, "mm", (-0.2, 0.2))
    assert fact.source.source == "document"
    assert fact.source.ref == "d0#p2:l7"
    assert fact.source.quote == "bore Ø82 ±0.2 mm"


def test_asymmetric_tolerance_keeps_both_deviations() -> None:
    [fact] = facts("Shaft: 20 +0.05/-0.02 mm")
    assert (fact.name, fact.value, fact.tol) == ("shaft", 20.0, (-0.02, 0.05))


@pytest.mark.parametrize("text", ["mount 4×M6", "mount 4x M6", "mount 4 X M6"])  # noqa: RUF001
def test_thread_callouts(text: str) -> None:
    [fact] = facts(text)
    assert (fact.kind, fact.value, fact.unit, fact.count) == ("holes", 6.0, "mm", 4)


def test_diameter_callout_and_thread_callout_on_one_line() -> None:
    found = facts("The plate has 6 x Ø6.6 holes and 4x M6 tapped holes.")
    assert [(f.kind, f.value, f.count) for f in found] == [("holes", 6.6, 6), ("holes", 6.0, 4)]


def test_requirement_ids_prefix_fact_names() -> None:
    assert summary("REQ-2: bore Ø82 ±0.2 mm") == [("tolerance", "req_2_bore", 82.0, "mm")]
    assert summary("REQ-1: mount 4×M6") == [("holes", "req_1_mount", 6.0, "mm")]  # noqa: RUF001


def test_size_chain_becomes_three_axis_facts() -> None:
    assert summary("Plate: 200 × 120 × 5 mm") == [  # noqa: RUF001
        ("parameter", "plate_size_x", 200.0, "mm"),
        ("parameter", "plate_size_y", 120.0, "mm"),
        ("parameter", "plate_size_z", 5.0, "mm"),
    ]


def test_key_value_lines() -> None:
    assert summary("wall_thickness = 3.2 mm") == [("parameter", "wall_thickness", 3.2, "mm")]
    assert summary("Part number: AX-1234") == [("parameter", "part_number", "AX-1234", "")]
    assert summary("count: 4") == [("parameter", "count", 4.0, "")]


def test_quantities_in_prose_are_named_by_preceding_words() -> None:
    assert summary("Computed wall thickness 3.2 mm from the sizing report.") == [("parameter", "computed_wall_thickness", 3.2, "mm")]
    assert summary("Overhang angle 45° max") == [("parameter", "overhang_angle", 45.0, "deg")]


@pytest.mark.parametrize(
    ("text", "material"),
    [
        ("Material: Al 6061-T6", "Al 6061"),
        ("aluminium 6082 bar", "Al 6082"),
        ("plate in S235JR", "S235"),
        ("frame S355", "S355"),
        ("stainless 1.4301", "1.4301"),
        ("printed in PLA", "PLA"),
        ("printed in PETG", "PETG"),
        ("ABS housing", "ABS"),
        ("SLS PA 12", "PA12"),
    ],
)
def test_materials(text: str, material: str) -> None:
    assert ("material", material) in [(f.kind, f.value) for f in facts(text)]


def test_standards() -> None:
    assert [f.value for f in facts("screws per ISO 4762 and flange EN 1092-1") if f.kind == "standard"] == ["ISO 4762", "EN 1092-1"]


def test_thread_designations_are_not_dimensions() -> None:
    assert facts("Use M6 screws") == []
