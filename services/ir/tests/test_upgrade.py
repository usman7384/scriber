from partwright_ir import Design, compile_design


def v1() -> dict[str, object]:
    return {
        "title": "Old",
        "params": [{"name": "t", "value": 5, "unit": "mm"}],
        "parts": [
            {
                "id": "p",
                "name": "P",
                "sketches": [{"id": "s", "plane": {"base": "XZ", "offset": 2}, "entities": [{"kind": "rect", "width": 10, "height": 10}]}],
                "features": [
                    {"kind": "extrude", "id": "e", "name": "E", "sketch": "s", "distance": "t", "symmetric": True},
                    {
                        "kind": "hole",
                        "id": "h",
                        "name": "H",
                        "plane": {"base": "XY"},
                        "at": {"kind": "points", "points": [[0, 0]]},
                        "diameter": 3,
                        "counterbore_diameter": 6,
                        "counterbore_depth": 2,
                    },
                    {"kind": "fillet", "id": "f", "name": "F", "edges": "top", "radius": 1},
                    {"kind": "shell", "id": "sh", "name": "S", "thickness": 1, "open_face": "bottom"},
                ],
            }
        ],
    }


def test_v1_designs_upgrade_on_load() -> None:
    d = Design.model_validate(v1())
    part = d.parts[0]
    assert d.ir_version == 2
    assert (part.sketches[0].plane.ref, part.sketches[0].plane.offset) == ("XZ", 2)
    extrude, hole, fillet, shell = part.features
    assert extrude.extent == "symmetric"  # type: ignore[union-attr]
    assert (hole.type, hole.cb_diameter, hole.cb_depth) == ("counterbore", 6, 2)  # type: ignore[union-attr]
    assert (fillet.edges.normal, fillet.edges.extreme) == ("+z", "max")  # type: ignore[union-attr]
    assert [(s.normal, s.extreme) for s in shell.open] == [("-z", "max")]  # type: ignore[union-attr]


def test_upgrade_is_idempotent_and_v2_round_trips() -> None:
    d = Design.model_validate(v1())
    again = Design.model_validate(d.model_dump(mode="json"))
    assert again == d
    assert compile_design(again) == compile_design(d)
