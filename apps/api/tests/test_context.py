import io
import json
from typing import Any

import httpx
from PIL import Image

from apps.api.tests.conftest import NO_REQS, Api, MakeApi, plate, until

SPEC = "# Base plate\n\nPlate length: {length} mm\nPlate width: 80 mm\nPlate thickness: 5 mm\nMounting holes: 4 x M6\n"


def upload(api: Api, project: str, name: str, content: bytes) -> dict[str, Any]:
    [job] = api.ok(api.client.post(f"/projects/{project}/context", files=[("files", (name, content, "application/octet-stream"))]))
    assert job["kind"] == "ingest"
    return api.wait(job["id"])


def spec(length: float = 120) -> bytes:
    return SPEC.format(length=f"{length:g}").encode()


def png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(out, format="PNG")
    return out.getvalue()


def listing(api: Api, project: str) -> dict[str, Any]:
    found: dict[str, Any] = api.ok(api.client.get(f"/projects/{project}/context"))
    return found


def plm(received: list[dict[str, Any]], failures: int = 0) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        received.append(json.loads(request.content))
        return httpx.Response(503 if len(received) <= failures else 200)

    return httpx.MockTransport(handle)


def test_uploaded_files_are_listed_with_facts(api: Api) -> None:
    project = api.project()
    assert upload(api, project, "spec.md", spec())["status"] == "done"
    [file] = listing(api, project)["files"]
    assert (file["name"], file["kind"], file["status"], file["facts"]) == ("spec.md", "md", "processed", 4)
    assert listing(api, project)["stats"]["files"] == 1
    facts = api.ok(api.client.get(f"/projects/{project}/context/{file['id']}/facts"))
    assert {f["name"]: f["value"] for f in facts}["plate_length"] == 120
    assert all(f["file_id"] == file["id"] and f["ref"] for f in facts)
    assert api.ok(api.client.get(f"/projects/{project}"))["file_count"] == 1
    graph = api.ok(api.client.get(f"/projects/{project}/graph"))
    assert graph["counts"]["document"] == 1 and {"id", "type", "name"} == set(graph["nodes"][0])


def test_unreadable_upload_is_a_failed_file(api: Api) -> None:
    project = api.project()
    job = upload(api, project, "notes.xyz", b"\x00\x01")
    [file] = listing(api, project)["files"]
    assert job["status"] == "failed" and file["status"] == "failed" and file["error"]


def test_rules_can_be_listed_and_overridden(api: Api) -> None:
    project = api.project()
    rules = {r["id"]: r for r in api.ok(api.client.get(f"/projects/{project}/rules"))}
    edge = {**rules["min_hole_edge_ratio"], "value": 2.0}
    assert api.ok(api.client.put(f"/projects/{project}/rules/min_hole_edge_ratio", json=edge))["value"] == 2.0
    assert {r["id"]: r["value"] for r in api.ok(api.client.get(f"/projects/{project}/rules"))}["min_hole_edge_ratio"] == 2.0
    assert api.client.put(f"/projects/{project}/rules/other", json=edge).status_code == 400
    assert api.client.put(f"/projects/{project}/rules/min_hole_edge_ratio", json={**edge, "kind": "nope"}).status_code == 422


def test_spec_change_marks_the_model_stale_and_notifies_hooks(make_api: MakeApi) -> None:
    received: list[dict[str, Any]] = []
    api = make_api(transport=plm(received))
    api.ok(api.client.post("/hooks", json={"url": "http://plm.test/hook", "events": ["version.stale"]}))
    project = api.project()
    upload(api, project, "spec.md", spec(120))
    [old] = listing(api, project)["files"]
    length = next(f for f in api.ok(api.client.get(f"/projects/{project}/context/{old['id']}/facts")) if f["name"] == "plate_length")
    model_id = api.generate(project, NO_REQS, plate(length_ref=length["id"]))["model_id"]
    version = api.ok(api.client.get(f"/models/{model_id}/versions/1"))
    assert [p["provenance"]["ref"] for p in version["params"] if p["name"] == "length"] == [length["ref"]]
    assert listing(api, project)["files"][0]["used_in"] == [model_id]

    upload(api, project, "spec.md", spec(130))
    after = listing(api, project)
    assert [f["name"] for f in after["files"]] == ["spec.md"] and after["files"][0]["id"] != old["id"]
    until(lambda: len(received) == 1)
    assert received == [
        {
            "event": "version.stale",
            "project_id": project,
            "file_id": old["id"],
            "model_id": model_id,
            "versions": [1],
            "changed_facts": [length["id"]],
        }
    ]
    until(lambda: api.ok(api.client.get(f"/models/{model_id}"))["latest_version"] == 2)
    [job] = [j for j in api.ok(api.client.get(f"/projects/{project}/jobs")) if j["kind"] == "params"]
    assert api.wait(job["id"])["status"] == "done"
    v1, v2 = api.ok(api.client.get(f"/models/{model_id}/versions"))
    assert v1["status"] == "ok" and v1["metrics"]["bbox"][0] == 120
    assert (v2["origin"], v2["prompt"]) == ("context", "spec.md changed: plate_length 120 -> 130 mm")
    assert v2["metrics"]["bbox"][0] == 130 and v2["changes"]["params"] == [{"name": "length", "old": 120.0, "new": 130.0}]
    [cited] = [p["provenance"] for p in v2["params"] if p["name"] == "length"]
    assert cited["source"] == "document" and cited["quote"] == "Plate length: 130 mm"
    assert listing(api, project)["stale"] == [] and listing(api, project)["files"][0]["used_in"] == [model_id]


def test_spec_change_without_a_cited_param_asks_the_model(api: Api) -> None:
    project = api.project()
    upload(api, project, "spec.md", spec(120))
    model_id = api.generate(project, NO_REQS, plate())["model_id"]
    api.llm.responses += [NO_REQS, json.dumps({"updates": [{"name": "length", "value": 130}], "design": None})]
    upload(api, project, "spec.md", spec(130))
    until(lambda: api.ok(api.client.get(f"/models/{model_id}"))["latest_version"] == 2)
    [job] = [j for j in api.ok(api.client.get(f"/projects/{project}/jobs")) if j["kind"] == "refine"]
    assert api.wait(job["id"])["status"] == "done"
    v2 = api.ok(api.client.get(f"/models/{model_id}/versions/2"))
    assert v2["origin"] == "context" and v2["metrics"]["bbox"][0] == 130
    assert "plate_length 120 -> 130 mm" in api.llm.calls[-1][-1].content


def test_deleting_a_used_file_marks_its_models_stale(api: Api) -> None:
    project = api.project()
    upload(api, project, "spec.md", spec())
    [file] = listing(api, project)["files"]
    length = next(f for f in api.ok(api.client.get(f"/projects/{project}/context/{file['id']}/facts")) if f["name"] == "plate_length")
    model_id = api.generate(project, NO_REQS, plate(length_ref=length["id"]))["model_id"]
    assert api.client.delete(f"/projects/{project}/context/{file['id']}").status_code == 204
    assert listing(api, project) | {"stats": None} == {"files": [], "stats": None, "stale": [model_id]}
    assert api.client.get(f"/projects/{project}/context/{file['id']}/facts").status_code == 404
    assert api.client.delete(f"/projects/{project}/context/{file['id']}").status_code == 404


def test_attachments_ground_the_design_and_are_recorded(api: Api) -> None:
    project = api.project()
    upload(api, project, "spec.md", spec())
    upload(api, project, "sketch.png", png())
    files = {f["name"]: f["id"] for f in listing(api, project)["files"]}
    both = [files["sketch.png"], files["spec.md"]]
    job = api.generate(project, NO_REQS, plate(), prompt="A plate like the sketch", attachments=both)
    version = api.ok(api.client.get(f"/models/{job['model_id']}/versions/1"))
    assert version["attachments"] == both and version["prompt"] == "A plate like the sketch"
    assert "Plate length: 120 mm" in api.llm.calls[-1][-1].content and api.llm.calls[-1][-1].images == (png(),)
    roles = [(i["kind"], i["name"], i["role"]) for i in version["inputs"]]
    assert roles == [("prompt", None, "used"), ("file", "sketch.png", "used"), ("file", "spec.md", "used")]
    assert any("Mounting holes" in c["description"] and c["passed"] for c in version["checks"])

    calls = len(api.llm.calls)
    job = api.generate(project, NO_REQS, plate(), prompt="A plate like the sketch", attachments=[files["sketch.png"]], context_ids=[])
    version = api.ok(api.client.get(f"/models/{job['model_id']}/versions/1"))
    assert "Plate length" not in api.llm.calls[calls + 1][-1].content and version["checks"] == []

    api.llm.responses += [NO_REQS, json.dumps({"updates": [{"name": "width", "value": 90}], "design": None})]
    body = {"instruction": "match the sketch", "attachments": [files["sketch.png"]]}
    refined = api.wait(api.ok(api.client.post(f"/models/{job['model_id']}/refine", json=body))["id"])
    assert api.ok(api.client.get(f"/models/{job['model_id']}/versions/{refined['version']}"))["attachments"] == [files["sketch.png"]]
    assert api.client.post(f"/projects/{project}/generate", json={"prompt": "x", "attachments": ["nope"]}).status_code == 400


def test_generate_validates_input(api: Api) -> None:
    project = api.project()
    assert api.client.post(f"/projects/{project}/generate", json={"prompt": ""}).status_code == 422
    assert api.client.post(f"/projects/{project}/generate", json={"prompt": "x", "process": "laser"}).status_code == 422
    assert api.client.post("/projects/nope/generate", json={"prompt": "x"}).status_code == 404


def test_selected_context_is_exactly_what_the_version_used(api: Api) -> None:
    project = api.project()
    for name, length in (("a.md", 120), ("b.md", 130), ("c.md", 140)):
        upload(api, project, name, spec(length))
    files = {f["name"]: f["id"] for f in listing(api, project)["files"]}
    chosen = [files["a.md"], files["b.md"]]
    job = api.generate(project, NO_REQS, plate(), prompt="Base plate", context_ids=chosen)
    version = api.ok(api.client.get(f"/models/{job['model_id']}/versions/1"))
    assert [i["id"] for i in version["inputs"] if i["kind"] == "file" and i["role"] == "used"] == chosen
    used_in = {f["name"]: f["used_in"] for f in listing(api, project)["files"]}
    assert used_in == {"a.md": [job["model_id"]], "b.md": [job["model_id"]], "c.md": []}


def test_upload_takes_the_contract_field_name(api: Api) -> None:
    project = api.project()
    sent = [("files[]", ("a.md", spec(), "text/markdown")), ("files[]", ("b.md", spec(90), "text/markdown"))]
    jobs = api.ok(api.client.post(f"/projects/{project}/context", files=sent))
    assert [api.wait(j["id"])["status"] for j in jobs] == ["done", "done"]
    assert [f["name"] for f in listing(api, project)["files"]] == ["a.md", "b.md"]
    assert api.client.post(f"/projects/{project}/context", data={"x": "1"}).status_code == 422
