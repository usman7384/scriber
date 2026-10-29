import json
from typing import Any

import httpx
import pytest

from apps.api.tests.conftest import Api, MakeApi, until
from apps.api.tests.test_context import plm


def test_tokens_guard_every_route_when_enabled(make_api: MakeApi) -> None:
    api = make_api(auth="tokens")
    assert api.client.get("/health").status_code == 200
    assert api.client.get("/projects").status_code == 401
    first = api.ok(api.client.post("/tokens", json={"name": "ci"}))
    assert api.client.post("/tokens", json={"name": "second"}).status_code == 401
    assert api.client.get("/projects", headers={"Authorization": f"Bearer {first['token']}"}).status_code == 200
    assert api.client.get("/projects", headers={"X-API-Token": first["token"]}).status_code == 200
    body = {"model_id": "m", "format": "glb"}
    assert api.client.post("/api/v1/download", json=body, headers={"X-API-Token": "wrong"}).status_code == 401
    headers = {"X-API-Token": first["token"]}
    second = api.ok(api.client.post("/tokens", json={"name": "second"}, headers=headers))
    listed = api.ok(api.client.get("/tokens", headers=headers))
    assert [t["name"] for t in listed] == ["ci", "second"] and all("token" not in t for t in listed)
    assert api.client.delete(f"/tokens/{second['id']}", headers=headers).status_code == 204
    assert api.client.get("/projects", headers={"X-API-Token": second["token"]}).status_code == 401
    assert api.client.delete(f"/tokens/{second['id']}", headers=headers).status_code == 404


def test_no_auth_by_default(api: Api) -> None:
    assert api.client.get("/projects").status_code == 200
    tools = {"freecad": False, "prusaslicer": False}
    assert api.ok(api.client.get("/health")) == {"status": "ok", "model": "fake", "ollama": False, "tools": tools}


def test_share_links_are_read_only_and_revocable(make_api: MakeApi) -> None:
    api = make_api(auth="tokens")
    headers = {"X-API-Token": api.ok(api.client.post("/tokens", json={"name": "me"}))["token"]}
    api.client.headers.update(headers)
    model_id = api.generate(api.project())["model_id"]
    share = api.ok(api.client.post("/shares", json={"model_id": model_id}))
    for name in ("Authorization", "X-API-Token"):
        api.client.headers.pop(name, None)
    shared = api.ok(api.client.get(share["url"]))
    assert shared["id"] == model_id and shared["version"]["number"] == 1
    assert all(url.startswith(share["url"]) for url in [*shared["version"]["files"].values(), shared["thumbnail_url"]])
    assert api.client.get(shared["version"]["files"]["glb"]).content[:4] == b"glTF"
    assert api.client.get(shared["thumbnail_url"]).headers["content-type"] == "image/png"
    assert api.client.patch(f"/models/{model_id}/params", json={"values": {"width": 90}}).status_code == 401
    assert api.client.delete(f"/shares/{share['id']}", headers=headers).status_code == 204
    assert api.client.get(share["url"]).status_code == 404
    assert api.client.get(f"{share['url']}/files/glb").status_code == 404
    assert api.client.post("/shares", json={"model_id": model_id, "version": 7}, headers=headers).status_code == 404


def test_webhook_retries_on_server_errors(make_api: MakeApi) -> None:
    received: list[dict[str, Any]] = []
    api = make_api(transport=plm(received, failures=2))
    hook = api.ok(api.client.post("/hooks", json={"url": "http://plm.test/hook", "events": ["version.created"]}))
    model_id = api.generate(api.project())["model_id"]
    until(lambda: len(received) == 3)
    assert received[0] == received[2]
    assert {k: received[2][k] for k in ("event", "model_id", "version")} == {"event": "version.created", "model_id": model_id, "version": 1}
    assert received[2]["files"]["step"] == f"http://127.0.0.1:8000/models/{model_id}/export?fmt=step&version=1"
    assert api.client.delete(f"/hooks/{hook['id']}").status_code == 204
    assert api.client.delete(f"/hooks/{hook['id']}").status_code == 404


def test_failed_jobs_notify_hooks_and_log_with_ids(make_api: MakeApi, capsys: pytest.CaptureFixture[str]) -> None:
    received: list[dict[str, Any]] = []
    api = make_api(transport=plm(received))
    api.ok(api.client.post("/hooks", json={"url": "http://plm.test/hook", "events": ["job.failed"]}))
    job = api.generate(api.project(), *["not json"] * 5)
    until(lambda: len(received) == 1)
    assert received[0]["event"] == "job.failed" and received[0]["job"]["id"] == job["id"]
    lines = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith("{")]
    [finished] = [line for line in lines if line["event"] == "job_finished"]
    assert finished["job_id"] == job["id"] and finished["request_id"] and finished["status"] == "failed"
    assert all("request_id" in line for line in lines if line["event"] == "request")


def test_generation_needs_a_reachable_ollama(make_api: MakeApi) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    api = make_api(transport=httpx.MockTransport(down), ollama_host="http://127.0.0.1:11434")
    project = api.project()
    response = api.client.post(f"/projects/{project}/generate", json={"prompt": "plate"})
    assert response.status_code == 503 and "Ollama" in response.json()["detail"]
    assert api.ok(api.client.get("/health"))["ollama"] is False
