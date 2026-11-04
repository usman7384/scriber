import ast

from scriber_ir import Design, compile_design


def test_compiled_source_is_python_and_parametric(bracket: Design) -> None:
    src = compile_design(bracket)
    ast.parse(src)
    assert "'plate_length': 80.0" in src
    assert "P['plate_length'] - 2 * P['hole_margin']" in src
    assert "# mount_holes Mounting holes" in src


def test_compile_is_deterministic(bracket: Design) -> None:
    assert compile_design(bracket) == compile_design(Design.model_validate(bracket.model_dump()))
