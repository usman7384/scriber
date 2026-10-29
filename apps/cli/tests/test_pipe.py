from dataclasses import dataclass
from typing import Any

import pytest

from partwright_cli.pipe import pipe


@dataclass
class Reply:
    body: Any
    is_success: bool = True

    @property
    def text(self) -> str:
        return str(self.body)

    def json(self) -> Any:
        return self.body


class Server:
    def __init__(self, *jobs: dict[str, Any]) -> None:
        self.jobs = list(jobs)
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> Reply:
        self.posts.append((url, kwargs))
        return Reply({"id": "p1"} if url == "/projects" else self.jobs.pop(0))

    def get(self, url: str) -> Reply:
        return Reply(self.jobs.pop(0))


def test_pipe_posts_the_xml_and_waits_for_the_job() -> None:
    server = Server({"id": "j", "status": "queued"}, {"id": "j", "status": "running"}, {"id": "j", "status": "done", "model_id": "m"})
    job = pipe(b"<aircraft/>", server, None, "wing.xml")
    assert job["model_id"] == "m"
    (_, project), (url, sent) = server.posts
    assert project["json"] == {"name": "pipe"} and url == "/projects/p1/sizing"
    assert sent["content"] == b"<aircraft/>" and sent["params"] == {"name": "wing.xml"}


def test_pipe_raises_on_an_api_error() -> None:
    server = Server()
    server.post = lambda url, **kw: Reply({"detail": "bad xml"}, is_success=False)  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="bad xml"):
        pipe(b"x", server, "p")
