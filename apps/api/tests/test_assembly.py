import json
from typing import Any

from apps.api.tests.conftest import NO_REQS, Api
from partwright_api import disk


def block(pid: str, size: float) -> dict[str, Any]:
    return {
        "id": pid,
        "name": pid.title(),
        "material": "PLA",
        "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": size, "height": size}]}],
        "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": size}],
    }


STACK = json.dumps(
    {
        "title": "Stack",
        "params": [],
        "parts": [block("plate", 40), block("cube", 10)],
        "assembly": {
            "connectors": [{"id": "seat", "part": "plate", "origin": [0, 0, 40]}, {"id": "foot", "part": "cube"}],
            "joints": [{"id": "cube_on_plate", "parent": "seat", "child": "foot"}],
        },
    }
)


def test_assembly_components_are_listed_with_ids_and_joints(api: Api) -> None:
    job = api.generate(api.project(), NO_REQS, STACK, prompt="a cube on a plate")
    assert job["status"] == "done", job
    listed = api.ok(api.client.get(f"/models/{job['model_id']}/components"))
    assert listed == [
        {"id": "plate", "name": "Plate", "material": "PLA", "parent": None, "joint": None},
        {"id": "cube", "name": "Cube", "material": "PLA", "parent": "plate", "joint": "cube_on_plate"},
    ]
    assert api.client.get(f"/models/{job['model_id']}/components", params={"version": 9}).status_code == 404


def test_targeted_refine_edits_only_that_component(api: Api) -> None:
    model_id = api.generate(api.project(), NO_REQS, STACK, prompt="a cube on a plate")["model_id"]
    cube = block("cube", 10)
    cube["features"] = [*cube["features"], {"kind": "chamfer", "id": "c", "name": "Chamfer", "edges": {}, "length": 1}]
    answer = json.dumps({"updates": [], "design": {"title": "Cube", "params": [], "parts": [cube]}})
    api.llm.responses += [NO_REQS, answer]
    job = api.wait(api.ok(api.client.post(f"/models/{model_id}/refine", json={"instruction": "chamfer it", "target": "cube"}))["id"])
    assert job["status"] == "done", job
    shown = api.llm.calls[-1][0].content
    assert '"id":"cube"' in shown and '"id":"plate"' not in shown
    before, after = (disk.design(disk.version_dir(api.deps.settings.data_dir, model_id, n)) for n in (1, 2))
    assert after.parts[0] == before.parts[0] and after.parts[1] != before.parts[1] and after.assembly == before.assembly
