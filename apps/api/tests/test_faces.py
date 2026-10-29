import pytest

from apps.api.tests.conftest import Api

TOP = {"point": [12.0, -7.5, 5.0], "normal": [0, 0, 1]}


def test_offsetting_the_top_face_changes_only_the_thickness(api: Api) -> None:
    model_id = api.generate(api.project())["model_id"]
    driver = api.ok(api.client.post(f"/models/{model_id}/face-driver", json=TOP))
    assert driver == {"part": "plate", "feature": "body", "param": "thickness", "rate": 1.0}
    before = api.ok(api.client.get(f"/models/{model_id}"))["version"]
    values = {p["name"]: p["value"] for p in before["params"]}
    new = values[driver["param"]] + 2 / driver["rate"]
    job = api.wait(api.ok(api.client.patch(f"/models/{model_id}/params", json={"values": {driver["param"]: new}}))["id"])
    assert job["status"] == "done", job
    after = api.ok(api.client.get(f"/models/{model_id}"))["version"]
    assert after["metrics"]["bbox"][2] == pytest.approx(before["metrics"]["bbox"][2] + 2, abs=0.01)
    assert {p["name"]: p["value"] for p in after["params"]} == values | {"thickness": 7}


def test_unknown_face_and_version_are_404(api: Api) -> None:
    model_id = api.generate(api.project())["model_id"]
    bottom = {"point": [0, 0, 0], "normal": [0, 0, -1]}
    assert api.client.post(f"/models/{model_id}/face-driver", json=bottom).status_code == 404
    assert api.client.post(f"/models/{model_id}/face-driver", json=TOP | {"version": 9}).status_code == 404
