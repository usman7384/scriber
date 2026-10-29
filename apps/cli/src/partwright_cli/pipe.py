import time
from typing import Any, Protocol


class Reply(Protocol):
    @property
    def is_success(self) -> bool: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


class Http(Protocol):
    def post(
        self,
        url: str,
        *,
        json: Any = ...,
        params: dict[str, str] | None = ...,
        content: bytes | None = ...,
        headers: dict[str, str] | None = ...,
    ) -> Reply: ...

    def get(self, url: str) -> Reply: ...


def pipe(xml: bytes, http: Http, project: str | None, name: str = "sizing.xml", timeout_s: float = 600) -> dict[str, Any]:
    project = project or _ok(http.post("/projects", json={"name": "pipe"}))["id"]
    headers = {"content-type": "application/xml"}
    job: dict[str, Any] = _ok(http.post(f"/projects/{project}/sizing", params={"name": name}, content=xml, headers=headers))
    deadline = time.monotonic() + timeout_s
    while job["status"] not in ("done", "failed"):
        if time.monotonic() > deadline:
            raise TimeoutError(f"job {job['id']} did not finish in {timeout_s:g} s")
        time.sleep(0.1)
        job = _ok(http.get(f"/jobs/{job['id']}"))
    return job


def _ok(reply: Reply) -> Any:
    if not reply.is_success:
        raise RuntimeError(f"API error: {reply.text[:300]}")
    return reply.json()
