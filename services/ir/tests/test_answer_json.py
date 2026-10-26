import json

from partwright_ir import Design, answer_json

SKETCH = {"id": "s", "plane": {"ref": "XZ"}, "entities": [{"kind": "rect", "width": 10, "height": 5}]}
PART = {
    "id": "p",
    "name": "P",
    "material": "POM",
    "sketches": [SKETCH],
    "features": [{"kind": "extrude", "id": "e", "name": "E", "sketch": "s", "distance": 3}],
}
DESIGN = Design.model_validate({"title": "T", "params": [], "parts": [PART]})


def test_required_keys_come_before_optional_ones() -> None:
    part = json.loads(answer_json(DESIGN))["parts"][0]
    assert list(part) == ["id", "name", "sketches", "features", "material"]
    assert list(part["sketches"][0]) == ["id", "entities", "plane"]


def test_defaults_are_left_out_and_the_answer_round_trips() -> None:
    text = answer_json(DESIGN)
    assert '"mode"' not in text and '"ir_version"' not in text
    assert Design.model_validate_json(text) == DESIGN
