import pytest

from scriber_context.parsed import Line
from scriber_context.rule_text import extract_rule, sentences


def rule(text: str) -> tuple[str, str, float, str, str, str] | None:
    found = extract_rule("d0", Line(1, 3, text), text)
    return None if found is None else (found.id, found.kind, found.value, found.unit, found.process, found.binding)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hole-to-edge distance at least 1.5 × D.", ("min_hole_edge_ratio", "min_hole_edge_ratio", 1.5, "", "any", "static")),  # noqa: RUF001
        ("Keep holes at least 2 diameters from any edge.", ("min_hole_edge_ratio", "min_hole_edge_ratio", 2.0, "", "any", "static")),
        ("Minimum wall thickness 2 mm", ("min_wall_thickness", "min_wall_thickness", 2.0, "mm", "any", "static")),
        (
            "Internal corners need a radius of at least 3 mm for milling.",
            ("min_internal_corner_radius@milling_3axis", "min_internal_corner_radius", 3.0, "mm", "milling_3axis", "static"),
        ),
        ("Overhangs must not exceed 45° (FDM).", ("max_overhang_angle@fdm", "max_overhang_angle", 45.0, "deg", "fdm", "static")),
        ("Holes should be at least 2.5 mm in diameter.", ("min_hole_diameter", "min_hole_diameter", 2.5, "mm", "any", "dynamic")),
        ("Parts must fit within 250 mm of build volume.", ("max_overall_size", "max_overall_size", 250.0, "mm", "any", "static")),
        ("SLA walls should be at least 0.04 in thick.", ("min_wall_thickness@sla", "min_wall_thickness", 1.016, "mm", "sla", "dynamic")),
    ],
)
def test_rule_sentences(text: str, expected: tuple[str, str, float, str, str, str]) -> None:
    assert rule(text) == expected


@pytest.mark.parametrize("text", ["Computed wall thickness 3.2 mm.", "The bracket is 80 mm long.", "Overhangs are fine."])
def test_statements_without_rule_wording_or_value_are_not_rules(text: str) -> None:
    assert rule(text) is None


def test_rule_records_its_source_and_severity_follows_binding() -> None:
    soft = extract_rule("d0", Line(2, 9, ""), "Holes should be at least 2.5 mm in diameter.")
    hard = extract_rule("d0", Line(2, 9, ""), "Minimum wall thickness 2 mm")
    assert soft is not None and hard is not None
    assert (soft.severity, hard.severity) == ("warning", "error")
    assert soft.source.ref == "d0#p2:l9"
    assert soft.text == "Holes should be at least 2.5 mm in diameter."


def test_wrapped_lines_join_into_one_sentence_and_keep_the_first_line() -> None:
    lines = [Line(1, 1, "Internal corners need a radius of at least"), Line(1, 2, "3 mm for milling."), Line(1, 3, "Minimum wall 2 mm")]
    assert [(line.number, s) for line, s in sentences(lines)] == [
        (1, "Internal corners need a radius of at least 3 mm for milling."),
        (3, "Minimum wall 2 mm"),
    ]


def test_sentences_split_inside_a_line_without_breaking_decimals() -> None:
    found = sentences([Line(1, 4, "Edge at least 1.5 × D. Walls min 2 mm.")])  # noqa: RUF001
    assert [s for _, s in found] == ["Edge at least 1.5 × D.", "Walls min 2 mm."]  # noqa: RUF001
