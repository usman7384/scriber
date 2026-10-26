from partwright_ir import Design, validate


def test_valid_design_has_no_errors(bracket: Design) -> None:
    assert validate(bracket) == []


def test_unknown_param_and_sketch_are_reported(bracket: Design) -> None:
    data = bracket.model_dump()
    data["parts"][0]["features"][0]["sketch"] = "missing"
    data["parts"][0]["features"][1]["diameter"] = "bolt_dia"
    errors = [str(e) for e in validate(Design.model_validate(data))]
    assert any("unknown sketch 'missing'" in e for e in errors)
    assert any("unknown parameter 'bolt_dia'" in e for e in errors)


def test_non_positive_dimension_is_reported(bracket: Design) -> None:
    data = bracket.model_dump()
    data["parts"][0]["features"][1]["diameter"] = "hole_margin - 10"
    assert any("must be > 0" in str(e) for e in validate(Design.model_validate(data)))


def test_first_feature_must_add_material(bracket: Design) -> None:
    data = bracket.model_dump()
    data["parts"][0]["features"].reverse()
    assert any("first feature" in str(e) for e in validate(Design.model_validate(data)))


def test_param_out_of_bounds_is_reported(bracket: Design) -> None:
    data = bracket.model_dump()
    data["params"][2]["value"] = 0.5
    assert any("outside" in str(e) for e in validate(Design.model_validate(data)))


def test_unused_parameter_is_reported(bracket: Design) -> None:
    data = bracket.model_dump()
    data["params"].append({"name": "orphan", "value": 3, "unit": "mm"})
    errors = [str(e) for e in validate(Design.model_validate(data))]
    assert errors == ["params.orphan: defined but not used; reference it in feature expressions instead of a literal number"]


def test_unused_sketch_is_reported(bracket: Design) -> None:
    data = bracket.model_dump()
    data["parts"][0]["sketches"].append({"id": "hole_circles", "entities": [{"kind": "circle", "diameter": 6}]})
    errors = [str(e) for e in validate(Design.model_validate(data))]
    assert len(errors) == 1
    assert errors[0].startswith("parts[0].sketches.hole_circles: is not used")


def test_overlapping_holes_are_reported(bracket: Design) -> None:
    data = bracket.model_dump()
    data["parts"][0]["features"].append(
        {
            "kind": "hole",
            "id": "bore",
            "name": "Bore",
            "plane": {"offset": 5},
            "at": {"kind": "points", "points": [[25, 15]]},
            "diameter": 20,
        }
    )
    errors = [str(e) for e in validate(Design.model_validate(data))]
    assert len(errors) == 1
    assert "overlap" in errors[0]
    assert "'mount_holes' at (30, 20)" in errors[0]


def hole(hid: str, x: float, d: float, offset: float = 5, depth: float | None = None, base: str = "XY") -> dict[str, object]:
    at = {"kind": "points", "points": [[x, 0]]}
    return {"kind": "hole", "id": hid, "name": hid, "plane": {"base": base, "offset": offset}, "at": at, "diameter": d, "depth": depth}


def with_holes(bracket: Design, *holes: dict[str, object]) -> list[str]:
    data = bracket.model_dump()
    data["parts"][0]["features"] = [data["parts"][0]["features"][0], *holes]
    data["params"] = [p for p in data["params"] if p["name"] in ("plate_length", "plate_width", "thickness")]
    return [str(e) for e in validate(Design.model_validate(data))]


def test_blind_holes_at_different_depths_may_share_a_projection(bracket: Design) -> None:
    assert with_holes(bracket, hole("top", 0, 10, offset=5, depth=2), hole("bottom", 3, 10, offset=1, depth=1)) == []


def test_concentric_holes_form_a_stepped_bore(bracket: Design) -> None:
    assert with_holes(bracket, hole("bore", 0, 6), hole("step", 0, 12, depth=2)) == []


def test_crossing_passages_on_different_axes_are_allowed(bracket: Design) -> None:
    assert with_holes(bracket, hole("vertical", 0, 4), hole("sideways", 0, 3, offset=0, base="YZ")) == []


def test_through_holes_that_collide_are_reported(bracket: Design) -> None:
    errors = with_holes(bracket, hole("a", 0, 10), hole("b", 6, 10))
    assert len(errors) == 1
    assert "overlap at the same depth" in errors[0]
