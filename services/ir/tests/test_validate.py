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


def test_fine_pitch_and_large_fasteners_are_accepted(bracket: Design) -> None:
    data = bracket.model_dump()
    data["parts"][0]["features"].append(
        {
            "kind": "hole",
            "id": "port",
            "name": "Port",
            "plane": {"ref": "XY", "offset": 5},
            "at": {"kind": "points", "points": [[0, 0]]},
            "type": "tapped",
            "fastener": "M18x1.5",
            "depth": 3,
        }
    )
    data["parts"][0]["features"][1]["fastener"] = "M30"
    data["parts"][0]["features"][1]["diameter"] = None
    errors = [str(e) for e in validate(Design.model_validate(data))]
    assert not any("fastener" in e for e in errors), errors


def test_unknown_fastener_and_zero_distance2_rules() -> None:
    base = {"id": "s", "entities": [{"kind": "rect", "width": 10, "height": 10}]}
    hole = {
        "kind": "hole",
        "id": "h",
        "name": "H",
        "plane": {"ref": "XY"},
        "at": {"kind": "points", "points": [[0, 0]]},
        "fastener": "G1/4",
    }
    body = {"kind": "extrude", "id": "b", "name": "B", "sketch": "s", "distance": 5, "distance2": 0}
    d = Design.model_validate(
        {"title": "x", "params": [], "parts": [{"id": "p", "name": "P", "sketches": [base], "features": [body, hole]}]}
    )
    errors = [str(e) for e in validate(d)]
    assert any("unknown fastener 'G1/4'" in e for e in errors)
    assert not any("distance2" in e for e in errors)


def test_revolve_across_its_axis_and_sketch_as_pattern_source_are_explained() -> None:
    disc = {"id": "s", "entities": [{"kind": "circle", "diameter": 20}]}
    base = {"id": "b", "entities": [{"kind": "rect", "width": 40, "height": 40}]}
    feats = [
        {"kind": "extrude", "id": "block", "name": "B", "sketch": "b", "distance": 5},
        {"kind": "revolve", "id": "boss", "name": "Boss", "sketch": "s", "axis": "Y"},
        {"kind": "pattern", "id": "copies", "name": "C", "features": ["s"], "type": "mirror"},
    ]
    d = Design.model_validate(
        {"title": "x", "params": [], "parts": [{"id": "p", "name": "P", "sketches": [base, disc], "features": feats}]}
    )
    errors = " ".join(str(e) for e in validate(d))
    assert "crosses the revolve axis" in errors
    assert "'s' is a sketch; list the feature that uses it" in errors
    assert "['block', 'boss']" in errors


def test_bad_expression_in_a_revolved_sketch_is_reported_not_raised() -> None:
    section = {"id": "s", "entities": [{"kind": "polygon", "points": [[1, 0], ["pi()", 0], [2, 5]]}]}
    feats = [{"kind": "revolve", "id": "r", "name": "R", "sketch": "s", "axis": "Y"}]
    d = Design.model_validate({"title": "x", "params": [], "parts": [{"id": "p", "name": "P", "sketches": [section], "features": feats}]})
    assert any("unknown function" in str(e) for e in validate(d))


def test_untabulated_sizes_interpolate() -> None:
    from partwright_ir.fasteners import parse, row

    assert parse("M25x1.5") == (25.0, 1.5)
    clearance, pitch, _ = row(25)
    assert 26.0 < clearance[1] < 30.0
    assert pitch == 3.0
    assert parse("M40") is None


def test_feature_params_follow_each_feature_and_its_sketch() -> None:
    from partwright_ir import Design, feature_params

    design = Design.model_validate(
        {
            "title": "Plate",
            "params": [
                {"name": "length", "value": 80, "unit": "mm"},
                {"name": "thickness", "value": 5, "unit": "mm"},
                {"name": "hole_d", "value": 6, "unit": "mm"},
            ],
            "parts": [
                {
                    "id": "p",
                    "name": "Plate",
                    "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "length", "height": 60}]}],
                    "features": [
                        {"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": "thickness"},
                        {
                            "kind": "hole",
                            "id": "h",
                            "name": "Hole",
                            "plane": {"offset": "thickness"},
                            "at": {"kind": "points", "points": [[0, 0]]},
                            "diameter": "hole_d",
                        },
                    ],
                }
            ],
        }
    )
    assert feature_params(design) == {("p", "body"): ["length", "thickness"], ("p", "h"): ["thickness", "hole_d"]}
