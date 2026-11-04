import json
from pathlib import Path
from typing import Any

from scriber_agent import FakeLLM, place, refine
from scriber_geometry import Artifact
from scriber_ir import Design, Process, RuleSet, joint_tree, part_hash

NO_REQS = json.dumps({"requirements": []})
NO_RULES = RuleSet()


class StubGeometry:
    def __init__(self) -> None:
        self.built: list[Design] = []

    def build(self, d: Design, out_dir: Path, rules: RuleSet = NO_RULES, process: Process = "any") -> Artifact:
        self.built.append(d)
        return Artifact(design_hash="x", files={}, parts=[], findings=[], elapsed_ms=0)


def block(pid: str, size: str) -> dict[str, Any]:
    return {
        "id": pid,
        "name": pid.title(),
        "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": size, "height": size}]}],
        "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": size}],
    }


BOX = Design.model_validate(
    {
        "title": "Box",
        "params": [{"name": "base_size", "value": 40, "unit": "mm"}, {"name": "lid_size", "value": 40, "unit": "mm"}],
        "parts": [block("base", "base_size"), block("lid", "lid_size")],
        "assembly": {
            "connectors": [
                {"id": "seat", "part": "base", "origin": [0, 0, "base_size"]},
                {"id": "lid_bottom", "part": "lid", "origin": [0, 0, 0]},
            ],
            "joints": [{"id": "lid_on_base", "parent": "seat", "child": "lid_bottom"}],
        },
    }
)


def test_targeted_refine_shows_only_the_target_and_keeps_the_rest(tmp_path: Path) -> None:
    lid = block("lid", "lid_size")
    edited = {"title": "Lid", "params": [{"name": "lid_size", "value": 40, "unit": "mm"}], "parts": [lid]}
    lid["features"].append({"kind": "chamfer", "id": "c", "name": "Chamfer", "edges": {}, "length": 1})
    llm = FakeLLM([NO_REQS, json.dumps({"updates": [], "design": edited})])
    steps = list(refine(BOX, "chamfer the lid", llm, StubGeometry(), tmp_path, target="lid"))
    result = steps[-1].result
    assert steps[-1].kind == "done" and result and result.design
    shown = llm.calls[1][0].content
    assert '"id":"lid"' in shown and '"id":"base"' not in shown
    assert part_hash(result.design, "base") == part_hash(BOX, "base")
    assert part_hash(result.design, "lid") != part_hash(BOX, "lid")
    assert result.design.assembly == BOX.assembly


def test_place_mates_a_new_part_and_repairs_a_missing_connector(tmp_path: Path) -> None:
    peg: dict[str, Any] = {"title": "Peg", "params": [{"name": "peg_size", "value": 5, "unit": "mm"}], "parts": [block("peg", "peg_size")]}
    with_connector = {**peg, "assembly": {"connectors": [{"id": "peg_foot", "part": "peg"}]}}
    llm = FakeLLM([json.dumps(peg), json.dumps(with_connector)])
    steps = list(place("a 5 mm peg", BOX, "seat", llm, StubGeometry(), tmp_path))
    assert "exactly one connector" in steps[1].message
    result = steps[-1].result
    assert steps[-1].kind == "done" and result and result.design
    assert joint_tree(result.design)["peg"][1] == "base"
    assert "connector 'seat'" in llm.calls[0][-1].content
