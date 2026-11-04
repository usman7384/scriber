import ast

import pytest

from scriber_ir import Design, compile_design, validate
from scriber_ir.airfoil import naca4


def test_symmetric_section_is_twelve_percent_thick_near_thirty_percent_chord() -> None:
    points = naca4("0012", 200)
    upper = points[:201]
    x, y = max(upper, key=lambda p: p[1])
    assert 2 * y == pytest.approx(0.12, abs=1e-4)
    assert x == pytest.approx(0.30, abs=0.01)


def test_cambered_section_runs_trailing_edge_to_leading_edge_and_back() -> None:
    points = naca4("2412", 100)
    assert len(points) == 201
    assert points[100] == pytest.approx((0.0, 0.0))
    assert points[0][0] == pytest.approx(1.0, abs=1e-3)
    assert points[-1][0] == pytest.approx(1.0, abs=1e-3)
    camber = [(up[1] + low[1]) / 2 for up, low in zip(points[100::-1], points[100:], strict=True)]
    assert max(camber) == pytest.approx(0.02, abs=1e-3)


def test_wing_validates_and_compiles_with_the_airfoil_prelude(wing: Design) -> None:
    assert validate(wing) == []
    src = compile_design(wing)
    ast.parse(src)
    assert "def naca4(" in src
    assert "T['tip_airfoil'] = pl * _airfoil('2412', P['tip_chord'], " in src
    assert "loft([T['root_airfoil'], T['tip_airfoil']], ruled=True)" in src


def test_designs_without_airfoils_skip_the_airfoil_prelude(bracket: Design) -> None:
    assert "naca4" not in compile_design(bracket)


def test_loft_needs_earlier_airfoil_sections(wing: Design) -> None:
    data = wing.model_dump()
    data["parts"][0]["features"][2]["sections"] = ["root_airfoil", "wingtip"]
    assert any("'wingtip' is not an earlier airfoil_section" in str(e) for e in validate(Design.model_validate(data)))


def test_invalid_naca_codes_are_reported(wing: Design) -> None:
    data = wing.model_dump()
    data["parts"][0]["features"][0]["naca"] = "2012"
    data["parts"][0]["features"][1]["naca"] = "0000"
    errors = [str(e) for e in validate(Design.model_validate(data))]
    assert any("NACA 2012" in e for e in errors)
    assert any("zero thickness" in e for e in errors)


def test_sections_are_not_solids_to_select_or_sketch_on(wing: Design) -> None:
    data = wing.model_dump()
    data["parts"][0]["features"].append({"kind": "fillet", "id": "f", "name": "f", "edges": {"of": "tip_airfoil"}, "radius": 1})
    assert any("airfoil section 'tip_airfoil'" in str(e) for e in validate(Design.model_validate(data)))
