import json
import threading
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, redirect_stderr
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Protocol

import httpx
from fastapi.testclient import TestClient

from partwright_agent import LLM, Message
from partwright_api import SerialGeometry, Settings, create_app
from partwright_api.logs import setup as setup_logs
from partwright_context import HashEmbedder, LocalContext
from partwright_evals.parity import Rig

NO_REQS = json.dumps({"requirements": []})


class Response(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def is_success(self) -> bool: ...

    @property
    def text(self) -> str: ...

    @property
    def content(self) -> bytes: ...

    @property
    def headers(self) -> Mapping[str, str]: ...

    def json(self) -> Any: ...


class Seeded:
    def __init__(self, answers: list[str], then: LLM | None = None) -> None:
        self.answers = list(answers)
        self.then = then
        self.name = then.name if then else "seeded"
        self.few_shot = then.few_shot if then else True
        self.calls = 0

    def chat(
        self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0, think: int | None = None
    ) -> str:
        self.calls += 1
        if self.answers:
            return self.answers.pop(0)
        if self.then is None:
            raise RuntimeError("the seeded answers ran out and no model follows them")
        return self.then.chat(messages, schema, seed, temperature, think)


class Gate:
    def __init__(self, inner: LLM) -> None:
        self.inner, self.name, self.few_shot = inner, inner.name, inner.few_shot
        self.open = threading.Event()

    def chat(
        self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0, think: int | None = None
    ) -> str:
        self.open.wait(60)
        return self.inner.chat(messages, schema, seed, temperature, think)


@dataclass
class Api:
    client: TestClient
    data: Path
    transcript: IO[str]

    def call(self, method: str, path: str, **kwargs: Any) -> Response:
        response: Response = self.client.request(method, path, **kwargs)
        self._record(method, path, kwargs, response)
        return response

    def ok(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.call(method, path, **kwargs)
        if not response.is_success:
            raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:300]}")
        return response.json()

    def wait(self, job_id: str, timeout: float = 1800) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job: dict[str, Any] = self.client.get(f"/jobs/{job_id}").json()
            if job["status"] in ("done", "failed"):
                self._record("GET", f"/jobs/{job_id}", {}, None, job)
                return job
            time.sleep(0.05)
        raise TimeoutError(f"job {job_id} did not finish in {timeout} s")

    def project(self, name: str = "Parity") -> str:
        project_id: str = self.ok("POST", "/projects", json={"name": name})["id"]
        return project_id

    def generate(self, project_id: str, prompt: str, **body: Any) -> dict[str, Any]:
        return self.wait(self.ok("POST", f"/projects/{project_id}/generate", json={"prompt": prompt, **body})["id"])

    def upload(self, project_id: str, name: str, content: bytes) -> dict[str, Any]:
        [job] = self.ok("POST", f"/projects/{project_id}/context", files=[("files", (name, content, "application/octet-stream"))])
        self.wait(job["id"])
        return next(f for f in self.ok("GET", f"/projects/{project_id}/context")["files"] if f["name"] == name)

    def version(self, model_id: str, number: int | None = None) -> dict[str, Any]:
        if number is None:
            latest: dict[str, Any] = self.ok("GET", f"/models/{model_id}")["version"]
            return latest
        found: dict[str, Any] = self.ok("GET", f"/models/{model_id}/versions/{number}")
        return found

    def result(self, model_id: str, number: int) -> dict[str, Any]:
        found: dict[str, Any] = json.loads((self.data / "models" / model_id / f"v{number}" / "result.json").read_text(encoding="utf-8"))
        return found

    def _record(self, method: str, path: str, kwargs: dict[str, Any], response: Response | None, body: Any = None) -> None:
        sent = kwargs.get("json") or ({"files": [f[1][0] for f in kwargs["files"]]} if "files" in kwargs else kwargs.get("params"))
        line: dict[str, Any] = {"time": round(time.time(), 3), "method": method, "path": path, "request": sent}
        if response is not None:
            line["status"] = response.status_code
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
            if body is None:
                line["bytes"], line["content_type"] = len(response.content), response.headers.get("content-type")
        line["response"] = body
        self.transcript.write(json.dumps(line) + "\n")
        self.transcript.flush()


@contextmanager
def serve(
    rig: Rig,
    llm: LLM,
    transport: httpx.AsyncBaseTransport | None = None,
    data: Path | None = None,
    vision: LLM | None = None,
    **settings: Any,
) -> Iterator[Api]:
    data = data or rig.out / "data"
    geometry = SerialGeometry(rig.geometry)
    try:
        with (
            (rig.out / "api.log").open("a", encoding="utf-8") as log,
            (rig.out / "transcript.jsonl").open("a", encoding="utf-8") as transcript,
            redirect_stderr(log),
            LocalContext(data / "context", HashEmbedder(), describe=geometry.describe) as context,
        ):
            settings = {"hook_backoff_s": 0.01, "seed": rig.config.agent.seed, "max_repairs": rig.config.agent.max_repairs, **settings}
            app = create_app(Settings(data_dir=data, **settings), llm, geometry, context, transport, vision)
            with TestClient(app) as client:
                yield Api(client, data, transcript)
    finally:
        # the API logs to whatever stderr was when it was built; point it back at the real one
        setup_logs()


def log_lines(rig: Rig) -> list[dict[str, Any]]:
    text = (rig.out / "api.log").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]
