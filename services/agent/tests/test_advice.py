import json

import pytest

from partwright_agent import FakeLLM, plan_variants, suggest
from partwright_geometry import Finding
from partwright_ir import Design

DESIGN = Design.model_validate(
    {
        "title": "Ribbed plate",
        "params": [
            {"name": "thickness", "value": 5, "unit": "mm", "min": 2},
            {"name": "rib_count", "value": 4, "unit": ""},
        ],
        "parts": [
            {
                "id": "p",
                "name": "Plate",
                "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": 100, "height": 40}]}],
                "features": [{"kind": "extrude", "id": "e", "name": "Plate", "sketch": "s", "distance": "thickness * rib_count"}],
            }
        ],
    }
)


def test_variant_plan_names_one_parameter_and_its_values() -> None:
    llm = FakeLLM([json.dumps({"param": "rib_count", "values": [4, 6, 8]})])
    plan = plan_variants(DESIGN, "3 versions with 4, 6, 8 ribs", llm)
    assert (plan.param, plan.values) == ("rib_count", [4, 6, 8])
    assert "3 versions with 4, 6, 8 ribs" in llm.calls[0][-1].content
    with pytest.raises(ValueError, match="not one of"):
        plan_variants(DESIGN, "x", FakeLLM([json.dumps({"param": "ribs", "values": [1]})]))


def test_suggestions_that_do_not_apply_are_dropped() -> None:
    answer = {
        "suggestions": [
            {"target": "thickness", "change": {"thickness": 6}, "rationale": "stiffer"},
            {"target": "thickness", "change": {"thickness": 1}, "rationale": "below its minimum"},
            {"target": "web", "change": {"web": 3}, "rationale": "unknown parameter"},
        ]
    }
    finding = Finding(rule_id="min_wall", severity="warning", message="wall 5 mm is thin", part="p")
    llm = FakeLLM([json.dumps(answer)])
    found = suggest(DESIGN, [finding], llm)
    assert [(s.target, s.change) for s in found] == [("thickness", {"thickness": 6})]
    assert "min_wall on p: wall 5 mm is thin" in llm.calls[0][-1].content
