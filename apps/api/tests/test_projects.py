from apps.api.tests.conftest import Api

CONTRACT = [
    ("get", "/health"),
    ("post", "/projects"),
    ("get", "/projects"),
    ("get", "/projects/{project_id}"),
    ("post", "/projects/{project_id}/context"),
    ("get", "/projects/{project_id}/context"),
    ("get", "/projects/{project_id}/context/{file_id}/facts"),
    ("delete", "/projects/{project_id}/context/{file_id}"),
    ("get", "/projects/{project_id}/rules"),
    ("put", "/projects/{project_id}/rules/{rule_id}"),
    ("get", "/projects/{project_id}/graph"),
    ("post", "/projects/{project_id}/generate"),
    ("get", "/projects/{project_id}/models"),
    ("get", "/models/{model_id}"),
    ("get", "/models/{model_id}/versions"),
    ("get", "/models/{model_id}/versions/{number}"),
    ("post", "/models/{model_id}/versions/{number}/restore"),
    ("post", "/models/{model_id}/refine"),
    ("patch", "/models/{model_id}/params"),
    ("get", "/models/{model_id}/export"),
    ("get", "/jobs/{job_id}"),
    ("get", "/jobs/{job_id}/events"),
    ("post", "/batch"),
    ("post", "/shares"),
    ("get", "/s/{share_id}"),
    ("delete", "/shares/{share_id}"),
    ("post", "/hooks"),
    ("delete", "/hooks/{hook_id}"),
    ("post", "/tokens"),
    ("get", "/tokens"),
    ("delete", "/tokens/{token_id}"),
    ("post", "/api/v1/generate"),
    ("post", "/api/v1/modify"),
    ("post", "/api/v1/edit"),
    ("post", "/api/v1/download"),
]


def test_openapi_lists_every_contract_route(api: Api) -> None:
    paths = api.ok(api.client.get("/openapi.json"))["paths"]
    assert [(m, p) for m, p in CONTRACT if m not in paths.get(p, {})] == []


def test_projects_are_created_listed_and_fetched(api: Api) -> None:
    created = api.ok(api.client.post("/projects", json={"name": "Brackets"}))
    assert (created["name"], created["model_count"], created["file_count"]) == ("Brackets", 0, 0)
    assert [p["id"] for p in api.ok(api.client.get("/projects"))] == [created["id"]]
    assert api.ok(api.client.get(f"/projects/{created['id']}")) == created
    assert api.client.post("/projects", json={"name": ""}).status_code == 422


def test_unknown_resources_are_404(api: Api) -> None:
    for path in ("/projects/nope", "/projects/nope/models", "/projects/nope/context", "/models/nope", "/models/nope/versions", "/s/nope"):
        response = api.client.get(path)
        assert response.status_code == 404 and response.json()["detail"], path


def test_hooks_validate_their_input(api: Api) -> None:
    assert api.client.post("/hooks", json={"url": "ftp://x", "events": ["version.created"]}).status_code == 422
    assert api.client.post("/hooks", json={"url": "http://x", "events": ["nope"]}).status_code == 422
    hook = api.ok(api.client.post("/hooks", json={"url": "http://x", "events": ["version.created", "job.failed"]}))
    assert hook["events"] == ["version.created", "job.failed"]
