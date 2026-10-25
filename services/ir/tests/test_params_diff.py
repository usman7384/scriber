import pytest

from partwright_ir import Design, ParamError, apply_params, diff, label


def test_apply_params_changes_value_and_provenance(bracket: Design) -> None:
    edited = apply_params(bracket, {"plate_length": 90})
    assert edited.param_values()["plate_length"] == 90
    assert next(p for p in edited.params if p.name == "plate_length").provenance.source == "user_edit"
    assert bracket.param_values()["plate_length"] == 80


def test_apply_params_rejects_unknown_and_out_of_bounds(bracket: Design) -> None:
    with pytest.raises(ParamError, match="unknown"):
        apply_params(bracket, {"nope": 1})
    with pytest.raises(ParamError, match="outside"):
        apply_params(bracket, {"thickness": 0.1})


def test_diff_reports_param_and_feature_changes(bracket: Design) -> None:
    data = apply_params(bracket, {"thickness": 8}).model_dump()
    data["parts"][0]["features"][1]["diameter"] = 9
    d = diff(bracket, Design.model_validate(data))
    assert [(c.name, c.old, c.new) for c in d.params] == [("thickness", 5, 8)]
    assert d.features_changed == ["bracket.mount_holes"]
    assert diff(bracket, bracket).empty


def test_label_is_title_case() -> None:
    assert label("base_bolt_spacing_x") == "Base Bolt Spacing X"
