import json

from apps.api.tests.conftest import NO_REQS, Api


def block(pid: str, size: float) -> dict[str, object]:
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
