from typing import Any

import pytest

from partwright_ir import (
    ComponentError,
    Design,
    compile_design,
    drop_unused_params,
    insert,
    joint_tree,
    part_hash,
    replace,
    scope,
    splice,
    validate,
)


def block(pid: str, size: str) -> dict[str, Any]:
    return {
        "id": pid,
        "name": pid.title(),
        "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": size, "height": size}]}],
        "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": size}],
    }


def connector(cid: str, part: str, z: Any = 0, **kw: Any) -> dict[str, Any]:
    return {"id": cid, "part": part, "origin": [0, 0, z], **kw}


def stack(**overrides: Any) -> Design:
    data = {
        "title": "Stack",
        "params": [{"name": "base", "value": 40, "unit": "mm"}, {"name": "top", "value": 10, "unit": "mm"}],
        "parts": [block("plate", "base"), block("cube", "top")],
        "assembly": {
            "connectors": [connector("seat", "plate", "base"), connector("foot", "cube")],
            "joints": [{"id": "cube_on_plate", "parent": "seat", "child": "foot"}],
        },
    }
    return Design.model_validate({**data, **overrides})


def messages(design: Design) -> list[str]:
    return [e.message for e in validate(design)]


def test_valid_assembly_compiles_mates_in_parent_order() -> None:
    design = stack()
    assert validate(design) == []
    source = compile_design(design)
    assert "MATES = [('cube_on_plate', 'plate', 'cube')]" in source
    assert "L['cube'] = L['plate'] * _mate(((0.0, 0.0, P['base']), '+z', '+x'), 0.0, 0.0, ((0.0, 0.0, 0.0), '+z', '+x'))" in source
    assert "'cube': part_1().moved(L['cube'])" in source
    assert joint_tree(design)["cube"][1] == "plate"


def test_params_used_only_by_connectors_are_kept() -> None:
    data = stack().model_dump(mode="json")
    data["params"].append({"name": "lift", "value": 2, "unit": "mm"})
    data["assembly"]["joints"][0]["offset"] = "lift"
    design = Design.model_validate(data)
    assert validate(design) == []
    assert "lift" in {p.name for p in drop_unused_params(design).params}


@pytest.mark.parametrize(
    ("assembly", "expected"),
    [
        ({"connectors": [connector("seat", "plate"), connector("foot", "ghost")], "joints": []}, "unknown part 'ghost'"),
        ({"connectors": [connector("seat", "plate", x="+z")], "joints": []}, "must be perpendicular"),
        (
            {"connectors": [connector("seat", "plate")], "joints": [{"id": "j", "parent": "seat", "child": "nowhere"}]},
            "unknown connectors ['nowhere']",
        ),
        (
            {"connectors": [connector("a", "plate"), connector("b", "plate")], "joints": [{"id": "j", "parent": "a", "child": "b"}]},
            "both connectors are on part 'plate'",
        ),
        (
            {
                "connectors": [connector("a", "plate"), connector("b", "cube"), connector("c", "plate")],
                "joints": [{"id": "j1", "parent": "a", "child": "b"}, {"id": "j2", "parent": "c", "child": "b"}],
            },
            "already placed by another joint",
        ),
        (
            {
                "connectors": [connector("a", "plate"), connector("b", "cube")],
                "joints": [{"id": "j1", "parent": "a", "child": "b"}, {"id": "j2", "parent": "b", "child": "a"}],
            },
            "joints form a loop",
        ),
        ({"connectors": [connector("seat", "plate", "height")], "joints": []}, "unknown parameter 'height'"),
    ],
)
def test_assembly_errors_name_the_problem(assembly: dict[str, Any], expected: str) -> None:
    assert any(expected in m for m in messages(stack(assembly=assembly))), messages(stack(assembly=assembly))


def test_scope_keeps_only_the_part_and_its_params() -> None:
    scoped = scope(stack(), "cube")
    assert [p.id for p in scoped.parts] == ["cube"]
    assert [p.name for p in scoped.params] == ["top"]
    assert scoped.assembly is None


def test_splice_replaces_one_part_and_leaves_the_others_hash() -> None:
    design = stack()
    edited = scope(design, "cube").model_copy(update={"title": "Edited"})
    data = edited.model_dump(mode="json")
    data["params"].append({"name": "chamfer", "value": 1, "unit": "mm"})
    data["parts"][0]["features"].append({"kind": "chamfer", "id": "c", "name": "Chamfer", "edges": {}, "length": "chamfer"})
    spliced = splice(design, Design.model_validate(data), "cube")
    assert part_hash(spliced, "plate") == part_hash(design, "plate")
    assert part_hash(spliced, "cube") != part_hash(design, "cube")
    assert spliced.assembly == design.assembly and spliced.title == "Stack"


def test_insert_mates_the_new_part_at_the_named_connector() -> None:
    peg = Design.model_validate(
        {
            "title": "Peg",
            "params": [{"name": "peg", "value": 5, "unit": "mm"}],
            "parts": [block("peg", "peg")],
            "assembly": {"connectors": [connector("peg_foot", "peg")]},
        }
    )
    placed = insert(stack(), peg, "seat")
    assert validate(placed) == []
    assert joint_tree(placed)["peg"][1] == "plate"
    with pytest.raises(ComponentError, match="no connector 'nowhere'"):
        insert(stack(), peg, "nowhere")
    with pytest.raises(ComponentError, match="exactly one connector"):
        insert(stack(), peg.model_copy(update={"assembly": None}), "seat")
    with pytest.raises(ComponentError, match="already used"):
        insert(placed, peg, "seat")


def test_replace_swaps_a_part_and_keeps_its_joints_through_matching_connectors() -> None:
    ball = {
        "title": "Ball",
        "params": [{"name": "ball", "value": 12, "unit": "mm"}],
        "parts": [block("rebuilt", "ball")],
        "assembly": {"connectors": [connector("foot", "rebuilt", "-ball / 2")]},
    }
    swapped = replace(stack(), Design.model_validate(ball), "cube")
    assert validate(swapped) == []
    assert [p.name for p in swapped.params] == ["base", "ball"]
    assert [p.id for p in swapped.parts] == ["plate", "cube"] and swapped.assembly is not None
    assert [j.id for j in swapped.assembly.joints] == ["cube_on_plate"]
    assert swapped.assembly.connectors[1].origin == (0, 0, "-ball / 2") and swapped.assembly.connectors[1].part == "cube"
    with pytest.raises(ComponentError, match=r"connectors \['foot'\]"):
        replace(stack(), Design.model_validate({**ball, "assembly": None}), "cube")
    with pytest.raises(ComponentError, match="other values"):
        replace(stack(), Design.model_validate({**ball, "params": [{"name": "base", "value": 1, "unit": "mm"}, *ball["params"]]}), "cube")
