import pytest

from scriber_ir import Design, Param, fit_limits, limits, validate


@pytest.mark.parametrize(
    ("size", "fit", "expected"),
    [
        (20, "H7", (0, 0.021)),
        (20, "g6", (-0.02, -0.007)),
        (20, "k6", (0.002, 0.015)),
        (20, "p6", (0.022, 0.035)),
        (50, "js7", (-0.0125, 0.0125)),
    ],
)
def test_iso_286_fits_give_the_table_limits(size: float, fit: str, expected: tuple[float, float]) -> None:
    assert fit_limits(size, fit) == pytest.approx(expected)


def test_limits_come_from_a_fit_or_from_deviations() -> None:
    assert limits(Param(name="bore", value=20, unit="mm", fit="H7")) == pytest.approx((20, 20.021))
    assert limits(Param(name="width", value=10, unit="mm", tol_plus=0.05, tol_minus=-0.02)) == pytest.approx((9.98, 10.05))
    assert limits(Param(name="plain", value=10, unit="mm")) is None


def test_bad_tolerances_are_explained() -> None:
    params = [
        {"name": "a", "value": 20, "unit": "mm", "fit": "Q7"},
        {"name": "b", "value": 5, "unit": "mm", "tol_plus": -0.1, "tol_minus": 0.1},
        {"name": "c", "value": 5, "unit": "mm", "fit": "h7", "tol_plus": 0.1},
    ]
    sketch = {"id": "s", "entities": [{"kind": "circle", "diameter": "a + b + c"}]}
    part = {
        "id": "p",
        "name": "P",
        "sketches": [sketch],
        "features": [{"kind": "extrude", "id": "x", "name": "X", "sketch": "s", "distance": 5}],
    }
    errors = [e.message for e in validate(Design.model_validate({"title": "t", "params": params, "parts": [part]}))]
    assert any("not in the table" in m for m in errors)
    assert any("is below tol_minus" in m for m in errors)
    assert any("not both" in m for m in errors)
