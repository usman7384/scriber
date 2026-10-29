from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

Vec = tuple[float, float, float]
Row = tuple[float, float, float, float]
Placement = tuple[Row, Row, Row]
FileKind = Literal["step", "stl", "glb", "py", "ir"]
STEP_SUFFIXES = frozenset({".step", ".stp"})
MESH_SUFFIXES = frozenset({".stl", ".obj"})
INTERFERENCE_MM3 = 1e-6
TOUCH_MM = 1e-6


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
    center_of_mass: Vec | None = None
    mass_g: float | None = None
    placement: Placement | None = None


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


class Interference(Frozen):
    a: str
    b: str
    volume: float


class MateCheck(Frozen):
    joint: str
    parent: str
    child: str
    gap: float


class AssemblyReport(Frozen):
    mates: list[MateCheck]
    interferences: list[Interference]
    mass_g: float | None = None
    center_of_mass: Vec | None = None

    def overlaps(self) -> list[Interference]:
        return [i for i in self.interferences if i.volume > INTERFERENCE_MM3]

    def broken_mates(self) -> list[str]:
        overlapping = {frozenset((i.a, i.b)) for i in self.overlaps()}
        return [m.joint for m in self.mates if m.gap > TOUCH_MM or frozenset((m.parent, m.child)) in overlapping]


class Artifact(Frozen):
    design_hash: str
    files: dict[FileKind, Path]
    parts: list[PartMetrics]
    findings: list[Finding]
    elapsed_ms: int
    assembly: AssemblyReport | None = None

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)


class BuildError(RuntimeError):
    def __init__(self, kind: Literal["kernel", "timeout", "crash"], message: str, feature: str | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.feature = feature
