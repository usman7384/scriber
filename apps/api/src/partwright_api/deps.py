import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Protocol, cast

import httpx
from fastapi import Depends, Request
from sqlalchemy import Engine

from partwright_agent import LLM
from partwright_api.hooks import Hooks
from partwright_api.jobs import Jobs
from partwright_api.settings import Settings
from partwright_context import Context
from partwright_geometry import Artifact, PartMetrics, PartStructure, SketchFrame
from partwright_ir import Design, Process, RuleSet, ShapeDescriptor

NO_RULES = RuleSet()


class Geometry(Protocol):
    def build(self, design: Design, out_dir: Path, rules: RuleSet = ..., process: Process = "any") -> Artifact: ...

    def describe(self, path: Path) -> ShapeDescriptor: ...

    def thumbnail(self, glb: Path, png: Path, size: int = 256) -> Path: ...

    def measure(self, design: Design) -> list[PartMetrics]: ...

    def frames(self, design: Design) -> list[SketchFrame]: ...

    def structure(self, design: Design) -> dict[str, PartStructure]: ...


class SerialGeometry:
    # One warm CAD worker serves every job; its pipe protocol takes one request at a time.
    def __init__(self, inner: Geometry) -> None:
        self._inner = inner
        self._lock = threading.Lock()

    def build(self, design: Design, out_dir: Path, rules: RuleSet = NO_RULES, process: Process = "any") -> Artifact:
        with self._lock:
            return self._inner.build(design, out_dir, rules, process)

    def describe(self, path: Path) -> ShapeDescriptor:
        with self._lock:
            return self._inner.describe(path)

    def thumbnail(self, glb: Path, png: Path, size: int = 256) -> Path:
        with self._lock:
            return self._inner.thumbnail(glb, png, size)

    def measure(self, design: Design) -> list[PartMetrics]:
        with self._lock:
            return self._inner.measure(design)

    def frames(self, design: Design) -> list[SketchFrame]:
        with self._lock:
            return self._inner.frames(design)

    def structure(self, design: Design) -> dict[str, PartStructure]:
        with self._lock:
            return self._inner.structure(design)


@dataclass(frozen=True)
class Deps:
    settings: Settings
    engine: Engine
    llm: LLM
    geometry: SerialGeometry
    context: Context
    http: httpx.AsyncClient
    hooks: Hooks
    jobs: Jobs
    vision: LLM | None = None
    context_lock: threading.Lock = field(default_factory=threading.Lock)


def deps(request: Request) -> Deps:
    return cast(Deps, request.app.state.deps)


DepsDep = Annotated[Deps, Depends(deps)]
