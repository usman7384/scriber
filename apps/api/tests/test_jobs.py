import json
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import inspect

from apps.api.tests.conftest import PROMPT, REQS, Api, MakeApi, plate
from partwright_api import jobs_db
from partwright_api.db import open_engine


def sse(lines: list[str]) -> list[tuple[str, str, dict[str, Any]]]:
    events, current = [], dict[str, str]()
    for line in lines:
        if not line:
            if "event" in current:
                events.append((current["event"], current["id"], json.loads(current["data"])))
            current = {}
        elif not line.startswith(":"):
            key, _, value = line.partition(": ")
            current[key] = value
    return events


def test_generate_streams_steps_then_done(api: Api) -> None:
    project = api.project()
    api.llm.responses += [REQS, '{"title": "x"}', plate()]
    job = api.ok(api.client.post(f"/projects/{project}/generate", json={"prompt": PROMPT}))
    assert job["status"] == "queued" and job["model_id"]
    with api.client.stream("GET", f"/jobs/{job['id']}/events") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        events = sse(list(response.iter_lines()))
    assert [e for e, _, _ in events] == ["step"] * 5 + ["done"]
    assert [d["kind"] for _, _, d in events[:-1]] == ["requirements", "emit", "check", "repair", "done"]
    assert [i for _, i, _ in events[:-1]] == ["0", "1", "2", "3", "4"]
    assert [d["progress"] for _, _, d in events[:-1]] == [10, 40, 60, 70, 100]
    final = events[-1][2]
    assert final["status"] == "done" and final["version"] == 1 and len(final["steps"]) == 5
    with api.client.stream("GET", f"/jobs/{job['id']}/events", headers={"Last-Event-ID": "3"}) as response:
        assert [(e, i) for e, i, _ in sse(list(response.iter_lines()))] == [("step", "4"), ("done", "5")]


def test_failed_generation_ends_with_a_failed_event(api: Api) -> None:
    project = api.project()
    job = api.generate(project, REQS, *[f"not json {i}" for i in range(4)])
    assert job["status"] == "failed" and "gave up" in job["error"]
    with api.client.stream("GET", f"/jobs/{job['id']}/events") as response:
        assert sse(list(response.iter_lines()))[-1][0] == "failed"
    version = api.ok(api.client.get(f"/models/{job['model_id']}/versions/1"))
    assert version["status"] == "failed" and version["files"] == {}


def test_running_jobs_become_interrupted_on_restart(make_api: MakeApi) -> None:
    first = make_api()
    project = first.project()
    job = jobs_db.create(first.deps.engine, "generate", project, None)
    jobs_db.start(first.deps.engine, job.id)
    second = make_api()
    found = second.ok(second.client.get(f"/jobs/{job.id}"))
    assert (found["status"], found["error"]) == ("failed", "interrupted")


def test_unknown_job_is_404(api: Api) -> None:
    assert api.client.get("/jobs/nope").status_code == 404
    assert api.client.get("/jobs/nope/events").status_code == 404


def test_project_jobs_list_newest_first_and_filter_active(make_api: MakeApi) -> None:
    api = make_api()
    project = api.project()
    done = api.generate(project, REQS, plate())
    queued = jobs_db.create(api.deps.engine, "generate", project, None)
    every = [j["id"] for j in api.ok(api.client.get(f"/projects/{project}/jobs"))]
    assert every == [queued.id, done["id"]]
    assert [j["id"] for j in api.ok(api.client.get(f"/projects/{project}/jobs?active=true"))] == [queued.id]


def test_job_keeps_its_full_request(api: Api) -> None:
    project = api.project()
    job = api.generate(project, REQS, plate(), prompt="a plate, " + "x" * 300)
    assert job["request"]["prompt"] == "a plate, " + "x" * 300
    assert api.ok(api.client.get(f"/jobs/{job['id']}"))["request"]["prompt"].endswith("x" * 300)


def test_old_database_gains_the_request_column(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as c:
        c.execute(
            "create table jobs (id text primary key, kind text not null, status text not null, project_id text not null, model_id text, "
            "version integer, error text, created text not null, started text, finished text)"
        )
    names = {col["name"] for col in inspect(open_engine(path)).get_columns("jobs")}
    assert "request" in names
