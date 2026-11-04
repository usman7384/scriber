from typing import Any

from scriber_ir import Design, compile_design, validate


def with_groups(bracket: Design, groups: list[dict[str, Any]]) -> Design:
    data = bracket.model_dump()
    data["parts"][0]["face_groups"] = groups
    return Design.model_validate(data)


def test_face_groups_compile_to_a_selection_per_name(bracket: Design) -> None:
    design = with_groups(bracket, [{"name": "mount_face", "faces": {"normal": "-z"}}])
    src = compile_design(design)
    assert "\nFACES = {}\n" in src
    assert "FACES['bracket'] = {'mount_face': _select(part, T, 'faces', 'part', '-z', 'any', 'any', 'any')}" in src
    assert validate(design) == []


def test_designs_without_face_groups_compile_unchanged(bracket: Design) -> None:
    assert "FACES" not in compile_design(bracket)


def test_face_group_errors_are_reported(bracket: Design) -> None:
    groups = [{"name": "load_face", "faces": {"of": "boss"}}, {"name": "load_face", "faces": {"normal": "+z"}}]
    errors = [str(e) for e in validate(with_groups(bracket, groups))]
    assert "parts[0].face_groups: duplicate face group name" in errors
    assert "parts[0].face_groups.load_face: selector refers to 'boss', which is not an earlier feature" in errors
