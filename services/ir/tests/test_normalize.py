from scriber_ir import Design, normalize, validate


def plate(params: list[dict[str, object]], diameter: object, count: object = 2) -> Design:
    hole = {
        "kind": "hole",
        "id": "h",
        "name": "H",
        "plane": {"offset": 0},
        "at": {"kind": "grid", "count_x": count, "count_y": 2, "spacing_x": 31, "spacing_y": 31},
        "diameter": diameter,
    }
    return Design.model_validate(
        {
            "title": "Plate",
            "params": [{"name": "size", "value": 60, "unit": "mm"}, *params],
            "parts": [
                {
                    "id": "p",
                    "name": "P",
                    "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "size", "height": "size"}]}],
                    "features": [{"kind": "extrude", "id": "e", "name": "E", "sketch": "s", "distance": 5}, hole],
                }
            ],
        }
    )


def test_literals_matching_unused_params_are_linked() -> None:
    d = normalize(plate([{"name": "pitch", "value": 31, "unit": "mm"}, {"name": "bolts_x", "value": 2, "unit": ""}], 3.4))
    at = d.parts[0].features[1].model_dump()["at"]
    assert (at["spacing_x"], at["spacing_y"], at["count_x"]) == ("pitch", "pitch", "bolts_x")
    assert validate(d) == []


def test_unit_mismatch_is_not_linked_and_unused_params_stay_visible() -> None:
    d = normalize(plate([{"name": "wall", "value": 2, "unit": "mm"}], 3.4))
    assert d.parts[0].features[1].model_dump()["at"]["count_x"] == 2
    assert [str(e) for e in validate(d)] == [
        "params.wall: defined but not used; reference it in feature expressions instead of a literal number"
    ]


def test_design_without_unused_params_is_unchanged() -> None:
    d = plate([], 3.4)
    assert normalize(d) is d
