from scriber_agent.standards import reference_data


def test_dn50_flange() -> None:
    (line,) = reference_data("DN50 PN16 flat flange")
    assert "outer diameter 165 mm, bolt circle 125 mm, 4 holes of 18 mm" in line


def test_nema17_pattern() -> None:
    (line,) = reference_data("NEMA 17 motor mount")
    assert "31.0 mm square" in line
    assert "+-15.5 mm" in line


def test_2020_extrusion() -> None:
    (line,) = reference_data("T-joint bracket for 2020 aluminium extrusion")
    assert "slot centres every 20 mm" in line


def test_3030_extrusion() -> None:
    (line,) = reference_data("Joining plate for 3030 aluminium extrusion")
    assert "slot centres every 30 mm" in line and "M6 T-nuts" in line


def test_unrelated_text_has_no_reference_data() -> None:
    assert reference_data("mounting bracket 80x60, 5 mm thick, M6 holes, designed in 2020") == []
