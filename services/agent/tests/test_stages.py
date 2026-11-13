import pytest

from scriber_agent.stages import Changes, merged
from scriber_ir import Design


def plate() -> Design:
    sketch = {"id": "s", "entities": [{"kind": "rect", "width": "w", "height": 40}]}
    features = [
        {"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": 5},
        {"kind": "hole", "id": "a", "name": "A", "plane": {"offset": 5}, "at": {"kind": "points", "points": [[0, 0]]}, "diameter": 4},
        {"kind": "hole", "id": "b", "name": "B", "plane": {"offset": 5}, "at": {"kind": "points", "points": [[20, 0]]}, "diameter": 4},
    ]
    part = {"id": "p", "name": "Plate", "sketches": [sketch], "features": features}
    return Design.model_validate({"title": "Plate", "params": [{"name": "w", "value": 60, "unit": "mm"}], "parts": [part]})


def test_changes_replace_in_place_add_at_the_end_and_remove() -> None:
    wider = {"kind": "hole", "id": "a", "name": "A", "plane": {"offset": 5}, "at": {"kind": "points", "points": [[0, 0]]}, "diameter": 6}
    extra = {"kind": "hole", "id": "c", "name": "C", "plane": {"offset": 5}, "at": {"kind": "points", "points": [[-20, 0]]}, "diameter": 3}
    change = Changes.model_validate(
        {"part": "p", "params": [{"name": "w", "value": 80, "unit": "mm"}], "features": [extra, wider], "remove": ["b"]}
    )
    out = merged(plate(), change)
    assert [f.id for f in out.parts[0].features] == ["body", "a", "c"]
    assert out.parts[0].features[1].diameter == 6 and out.param_values()["w"] == 80


def test_changes_to_an_unknown_part_are_refused() -> None:
    with pytest.raises(ValueError, match=r"the parts are \['p'\]"):
        merged(plate(), Changes(part="q"))
