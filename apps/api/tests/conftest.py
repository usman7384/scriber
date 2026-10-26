import json
import time
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from partwright_agent import FakeLLM
from partwright_api import SerialGeometry, Settings, create_app
from partwright_api.deps import Deps
from partwright_context import HashEmbedder, LocalContext
from partwright_geometry import LocalGeometry

PROMPT = "Base plate 120 x 80 x 5 mm with four 6.6 mm bolt holes"
REQS = json.dumps({"requirements": [{"kind": "extent", "description": "plate 120 mm", "value": 120}]})
NO_REQS = json.dumps({"requirements": []})


def plate(spacing_x: float = 85, count_x: int = 2, length_ref: str | None = None, title: str = "Base plate") -> str:
    length: dict[str, Any] = {"name": "length", "value": 120, "unit": "mm"}
    if length_ref:
        length["provenance"] = {"source": "document", "ref": length_ref}
    return json.dumps(
        {
            "title": title,
            "params": [
                length,
                {"name": "width", "value": 80, "unit": "mm"},
                {"name": "thickness", "value": 5, "unit": "mm"},
                {"name": "hole_d", "value": 6.6, "unit": "mm"},
                {"name": "bolt_spacing_x", "value": spacing_x, "unit": "mm"},
            ],
            "parts": [
                {
                    "id": "plate",
                    "name": "Plate",
                    "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "length", "height": "width"}]}],
                    "features": [
                        {"kind": "extrude", "id": "body", "name": "Plate", "sketch": "s", "distance": "thickness"},
                        {
                            "kind": "hole",
                            "id": "holes",
                            "name": "Bolt holes",
                            "plane": {"offset": "thickness"},
                            "at": {"kind": "grid", "count_x": count_x, "count_y": 2, "spacing_x": "bolt_spacing_x", "spacing_y": 50},
                            "diameter": "hole_d",
                        },
                    ],
                }
            ],
        }
    )


@dataclass
class Api:
    app: FastAPI
    client: TestClient
    llm: FakeLLM
    context: LocalContext

    @property
    def deps(self) -> Deps:
        d: Deps = self.app.state.deps
        return d

    def project(self, name: str = "Demo") -> str:
        project_id: str = self.ok(self.client.post("/projects", json={"name": name}))["id"]
        return project_id

    def generate(self, project_id: str, *answers: str, prompt: str = PROMPT, **body: Any) -> dict[str, Any]:
        self.llm.responses += list(answers or (REQS, plate()))
        return self.wait(self.ok(self.client.post(f"/projects/{project_id}/generate", json={"prompt": prompt, **body}))["id"])

    def wait(self, job_id: str, timeout: float = 120) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job: dict[str, Any] = self.ok(self.client.get(f"/jobs/{job_id}"))
            if job["status"] in ("done", "failed"):
                return job
            time.sleep(0.05)
        raise TimeoutError(f"job {job_id} did not finish")

    @staticmethod
    def ok(response: httpx2.Response) -> Any:  # Starlette's TestClient uses httpx2 when it is installed
        assert response.is_success, response.text
        return response.json()


def until(condition: Callable[[], bool], timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError("condition not met")
        time.sleep(0.05)


@pytest.fixture(scope="session")
def geometry() -> Iterator[SerialGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield SerialGeometry(g)
    g.close()


MakeApi = Callable[..., Api]


@pytest.fixture
def make_api(tmp_path: Path, geometry: SerialGeometry) -> Iterator[MakeApi]:
    with ExitStack() as stack:

        def make(transport: httpx.AsyncBaseTransport | None = None, **settings: Any) -> Api:
            llm = FakeLLM([])
            context = stack.enter_context(LocalContext(tmp_path / "data" / "context", HashEmbedder(), describe=geometry.describe))
            app = create_app(Settings(data_dir=tmp_path / "data", hook_backoff_s=0.01, **settings), llm, geometry, context, transport)
            return Api(app, stack.enter_context(TestClient(app)), llm, context)

        yield make


@pytest.fixture
def api(make_api: MakeApi) -> Api:
    return make_api()
