import pytest

from scriber_ir.expr import ExprError, evaluate, names, to_python


def test_evaluates_arithmetic_with_params() -> None:
    assert evaluate("a * 2 + max(b, 1)", {"a": 3, "b": 5}) == 11


def test_trig_uses_degrees() -> None:
    assert evaluate("sin(30)", {}) == pytest.approx(0.5)


def test_numbers_pass_through() -> None:
    assert evaluate(4.5, {}) == 4.5


@pytest.mark.parametrize("bad", ["__import__('os')", "a.b", "[1]", "'x'", "lambda: 1", "f(1)", "a if b else c"])
def test_rejects_unsafe_or_unknown_syntax(bad: str) -> None:
    with pytest.raises(ExprError):
        evaluate(bad, {"a": 1, "b": 1, "c": 1})


def test_unknown_parameter_is_reported() -> None:
    with pytest.raises(ExprError, match="unknown parameter 'width'"):
        evaluate("width / 2", {})


def test_names_exclude_functions() -> None:
    assert names("sqrt(a) + b") == {"a", "b"}


def test_to_python_subscripts_params_and_keeps_precedence() -> None:
    assert to_python("plate_length / 2 - sqrt(x)") == "(P['plate_length'] / 2 - sqrt(P['x']))"
    assert to_python("width") == "P['width']"
    assert evaluate(to_python("od - 2 * wall").replace("P['od']", "24").replace("P['wall']", "2") + " / 2", {}) == 10
