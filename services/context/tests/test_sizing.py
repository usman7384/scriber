from pathlib import Path

import pytest

from partwright_context.aircraft import aircraft_design
from partwright_context.sizing import XmlSizing
from partwright_ir import validate

WING = """<wing><airfoil>NACA 2412</airfoil><span unit="m">1.0</span><root_chord unit="mm">250</root_chord>
<tip_chord>120 mm</tip_chord><sweep unit="deg">20</sweep><dihedral unit="deg">5</dihedral><twist unit="deg">2</twist></wing>"""
BODY = '<body><airfoil>0018</airfoil><chord unit="mm">420</chord><width unit="mm">180</width></body>'
TAIL = '<tail><airfoil>NACA 0010</airfoil><span unit="mm">110</span><tip_chord unit="mm">70</tip_chord><sweep unit="deg">35</sweep></tail>'


def xml(tmp_path: Path, *groups: str) -> Path:
    path = tmp_path / "sizing.xml"
    path.write_text(f'<aircraft name="Test BWB">{"".join(groups)}</aircraft>', encoding="utf-8")
    return path


def test_reads_wing_values_in_mm_and_deg_with_their_source(tmp_path: Path) -> None:
    spec = XmlSizing().read(xml(tmp_path, WING, '<requirements><inner_volume unit="l">1.5</inner_volume></requirements>'))
    assert (spec.wing.naca, spec.wing.span.value, spec.wing.tip_chord.value, spec.wing.twist.value) == ("2412", 1000, 120, 2)
    assert spec.wing.span.provenance.ref == "sizing.xml#wing/span"
    assert spec.wing.span.provenance.quote == '<span unit="m">1.0</span>'
    assert spec.inner_volume_mm3 is not None and spec.inner_volume_mm3.value == 1.5e6
    assert spec.body is None and spec.tail is None


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        (WING.replace('<twist unit="deg">2</twist>', ""), "missing <wing/twist>"),
        (WING.replace("NACA 2412", "NACA 23012"), "NACA 4-digit"),
        (WING.replace('<sweep unit="deg">20</sweep>', '<sweep unit="mm">20</sweep>'), "deg-compatible"),
        (WING.replace("120 mm", "120"), "needs a number with a unit"),
    ],
)
def test_bad_input_names_the_element(tmp_path: Path, bad: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        XmlSizing().read(xml(tmp_path, bad))


def test_wing_design_is_valid_and_sourced(tmp_path: Path) -> None:
    design = aircraft_design(XmlSizing().read(xml(tmp_path, WING)))
    assert validate(design) == []
    assert [f.name for f in design.parts[0].features] == ["root_airfoil", "tip_airfoil", "main_wing", "full_aircraft"]
    assert {p.provenance.source for p in design.params} == {"document"}


def test_blended_wing_body_has_named_sections_in_build_order(tmp_path: Path) -> None:
    design = aircraft_design(XmlSizing().read(xml(tmp_path, WING, BODY, TAIL)))
    assert validate(design) == []
    assert [f.name for f in design.parts[0].features] == [
        *("root_airfoil", "mid_airfoil", "tip_airfoil", "main_wing"),
        *("winglet_root_airfoil", "winglet_tip_airfoil", "winglet", "winglet_assembly", "full_aircraft"),
    ]
    assert design.title == "Test BWB"


def test_body_wider_than_the_span_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="body width"):
        aircraft_design(XmlSizing().read(xml(tmp_path, WING, BODY.replace("180", "1200"))))
