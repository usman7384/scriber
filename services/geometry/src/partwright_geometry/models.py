from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

Vec = tuple[float, float, float]
FileKind = Literal["step", "stl", "glb", "py", "ir"]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class HoleInfo(Frozen):
    diameter: float
    axis: Vec
    center: Vec
    length: float


class PartMetrics(Frozen):
    id: str
    name: str
    volume: float
    bbox_min: Vec
    bbox_size: Vec
    solids: int
    faces: int
    valid: bool
    holes: list[HoleInfo]


class Location(Frozen):
    point: Vec
    face: str


class Finding(Frozen):
    rule_id: str
    severity: Literal["error", "warning"]
    message: str
    part: str | None = None
    binding: Literal["static", "dynamic"] = "static"
    measured: float | None = None
    required: float | None = None
    location: Location | None = None
    suggestion: str | None = None


class Artifact(Frozen):
    design_hash: str
    files: dict[FileKind, Path]
    parts: list[PartMetrics]
    findings: list[Finding]
    elapsed_ms: int

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)


class BuildError(RuntimeError):
    def __init__(self, kind: Literal["kernel", "timeout", "crash"], message: str, feature: str | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.feature = feature
