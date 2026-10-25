import io
import json
from typing import Any

import pytest
import trimesh

from apps.api.tests.conftest import NO_REQS, Api, plate
from apps.api.tests.test_models import holes
from partwright_api import disk

BASE_AND_BOSS = json.dumps(
    {
        "title": "Base and boss",
        "params": [{"name": "plate_t", "value": 5, "unit": "mm"}, {"name": "boss_d", "value": 20, "unit": "mm"}],
        "parts": [
            {
                "id": "base",
                "name": "Base",
                "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": 60, "height": 40}]}],
                "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": "plate_t"}],
            },
            {
                "id": "boss",
                "name": "Boss",
                "sketches": [{"id": "s", "plane": {"offset": 5}, "entities": [{"kind": "circle", "diameter": "boss_d"}]}],
                "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": 10}],
            },
        ],
    }
)


def generate(api: Api, *answers: str, prompt: str = "plate") -> dict[str, Any]:
    api.llm.responses += list(answers)
    return api.wait(api.ok(api.client.post("/api/v1/generate", json={"prompt": prompt}))["job_id"])


def parts(api: Api, model_id: str, number: int) -> dict[str, dict[str, Any]]:
    result = disk.version_dir(api.deps.settings.data_dir, model_id, number) / "result.json"
    return {p["id"]: p for p in json.loads(result.read_text(encoding="utf-8"))["artifact"]["parts"]}


def test_generate_alias_uses_the_default_project(api: Api) -> None:
    job = generate(api, NO_REQS, plate(), prompt="Design a metal bracket with angled support and screw holes")
    assert job["status"] == "done" and job["project_id"] == "default"
    assert api.ok(api.client.get("/projects/default"))["name"] == "Default"
    assert len(holes(api, job["model_id"], 1)) >= 1


def test_modify_alias_changes_the_thickness(api: Api) -> None:
    model_id = generate(api, NO_REQS, plate())["model_id"]
    api.llm.responses += [NO_REQS, json.dumps({"updates": [{"name": "thickness", "value": 15}], "design": None})]
    job = api.wait(api.ok(api.client.post("/api/v1/modify", json={"model_id": model_id, "prompt": "make it 10 mm thicker"}))["job_id"])
    version = api.ok(api.client.get(f"/models/{model_id}/versions/{job['version']}"))
    assert version["metrics"]["bbox"][2] == pytest.approx(15, abs=0.01)


def test_edit_alias_changes_only_that_component(api: Api) -> None:
    model_id = generate(api, NO_REQS, BASE_AND_BOSS)["model_id"]
    body = {"model_id": model_id, "component_id": "boss", "params": {"boss_d": 30}}
    job = api.wait(api.ok(api.client.post("/api/v1/edit", json=body))["job_id"])
    assert (job["kind"], job["status"]) == ("edit", "done"), job
    before, after = parts(api, model_id, 1), parts(api, model_id, 2)
    assert after["base"] == before["base"]
    assert after["boss"]["bbox_size"][0] == pytest.approx(30)
    version = api.ok(api.client.get(f"/models/{model_id}/versions/2"))
    assert version["origin"] == "edit" and version["changes"]["features_changed"] == []
    assert api.client.post("/api/v1/edit", json={**body, "params": {"plate_t": 6}}).status_code == 400
    assert api.client.post("/api/v1/edit", json={**body, "component_id": "nope"}).status_code == 400


def test_download_alias_returns_each_format(api: Api) -> None:
    model_id = generate(api, NO_REQS, plate())["model_id"]
    files = {fmt: api.client.post("/api/v1/download", json={"model_id": model_id, "format": fmt}) for fmt in ("glb", "step", "stl")}
    assert all(r.status_code == 200 for r in files.values())
    assert files["glb"].content[:4] == b"glTF" and files["step"].content.startswith(b"ISO-10303-21")
    assert trimesh.load_mesh(io.BytesIO(files["stl"].content), file_type="stl").is_watertight
    assert api.client.post("/api/v1/download", json={"model_id": "nope", "format": "glb"}).status_code == 404
