import base64
import json

from apps.api.tests.conftest import NO_REQS, Api, MakeApi, plate

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def users(api: Api, *names: str) -> list[dict[str, str]]:
    first = api.ok(api.client.post("/tokens", json={"name": names[0]}))["token"]
    api.client.headers.update({"X-API-Token": first})
    tokens = [first] + [api.ok(api.client.post("/tokens", json={"name": n}))["token"] for n in names[1:]]
    return [{"X-API-Token": t} for t in tokens]


def built(api: Api, headers: dict[str, str]) -> str:
    project = api.ok(api.client.post("/projects", json={"name": "P"}, headers=headers))["id"]
    response = api.client.post(f"/projects/{project}/designs", json={"design": json.loads(plate())}, headers=headers)
    model_id: str = api.wait(api.ok(response)["id"])["model_id"]
    return model_id


def test_bug_report_stores_model_version_text_and_screenshot(api: Api) -> None:
    model_id = built(api, {})
    shot = "data:image/png;base64," + base64.b64encode(PNG).decode()
    bug = api.ok(api.client.post("/bugs", json={"model_id": model_id, "version": 1, "text": "hole is off", "screenshot": shot}))
    assert (bug["model_id"], bug["version"], bug["text"], bug["user"]) == (model_id, 1, "hole is off", "local")
    assert api.client.get(bug["screenshot_url"]).content == PNG
    plain = api.ok(api.client.post("/bugs", json={"model_id": model_id, "version": 1, "text": "no shot"}))
    assert plain["screenshot_url"] is None
    assert [b["text"] for b in api.ok(api.client.get("/bugs", params={"model_id": model_id}))] == ["hole is off", "no shot"]
    fake = "data:image/png;base64," + base64.b64encode(b"not a png").decode()
    assert api.client.post("/bugs", json={"model_id": model_id, "version": 1, "text": "x", "screenshot": fake}).status_code == 422
    assert api.client.post("/bugs", json={"model_id": model_id, "version": 9, "text": "x"}).status_code == 404


def test_generation_limit_returns_429_per_user(make_api: MakeApi) -> None:
    api = make_api(auth="tokens", generation_limit=2)
    alice, bob = users(api, "alice", "bob")
    project = api.ok(api.client.post("/projects", json={"name": "P"}, headers=alice))["id"]
    for _ in range(2):
        api.llm.responses += [NO_REQS, plate()]
        response = api.client.post(f"/projects/{project}/generate", json={"prompt": "plate"}, headers=alice)
        assert response.status_code == 202
        api.wait(response.json()["id"])
    third = api.client.post(f"/projects/{project}/generate", json={"prompt": "plate"}, headers=alice)
    assert third.status_code == 429 and "alice" in third.text
    assert api.client.post("/batch", json={"project_id": project, "prompts": ["a", "b", "c"]}, headers=bob).status_code == 429
    assert api.ok(api.client.get("/usage", headers=alice)) == {"user": "alice", "generations": 2, "limit": 2}
    assert api.ok(api.client.get("/usage", headers=bob))["generations"] == 0


def test_generation_is_unlimited_by_default(api: Api) -> None:
    project = api.project()
    for _ in range(3):
        assert api.generate(project, NO_REQS, plate())["status"] == "done"
    assert api.ok(api.client.get("/usage")) == {"user": "local", "generations": 3, "limit": None}


def test_published_part_is_forked_by_another_user_with_provenance(make_api: MakeApi) -> None:
    api = make_api(auth="tokens")
    alice, bob = users(api, "alice", "bob")
    model_id = built(api, alice)
    published = api.ok(api.client.post("/community", json={"model_id": model_id}, headers=alice))
    [listed] = api.ok(api.client.get("/community", headers=bob))
    assert listed["id"] == published["id"] and (listed["author"], listed["version"]) == ("alice", 1)
    project = api.ok(api.client.post("/projects", json={"name": "Bob"}, headers=bob))["id"]
    fork = api.ok(api.client.post(f"/community/{published['id']}/fork", json={"project_id": project}, headers=bob))
    source = {"publication": published["id"], "model_id": model_id, "version": 1, "title": "Base plate", "author": "alice"}
    assert fork["forked_from"] == source
    assert fork["project_id"] == project and fork["version"]["origin"] == "fork"
    job = api.client.patch(f"/models/{fork['id']}/params", json={"values": {"thickness": 8}}, headers=bob)
    assert api.wait(job.json()["id"])["status"] == "done"
    assert api.ok(api.client.get(f"/models/{fork['id']}", headers=bob))["version"]["metrics"]["bbox"][2] == 8
    assert api.ok(api.client.get(f"/models/{model_id}", headers=alice))["version"]["metrics"]["bbox"][2] == 5
    assert api.client.delete(f"/community/{published['id']}", headers=bob).status_code == 403
    assert api.client.delete(f"/community/{published['id']}", headers=alice).status_code == 204
