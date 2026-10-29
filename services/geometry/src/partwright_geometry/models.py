from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from partwright_ir import Design

Vec = tuple[float, float, float]
FileKind = Literal["step", "stl", "glb", "py", "ir"]
STEP_SUFFIXES = frozenset({".step", ".stp"})
MESH_SUFFIXES = frozenset({".stl", ".obj"})


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


class FaceGroupInfo(Frozen):
    name: str
    faces: int
    area: float
    center: Vec
    normal: Vec | None


class StepBody(Frozen):
    name: str
    material: str | None
    density_g_cm3: float | None
    face_groups: list[FaceGroupInfo]


class StepMetadata(Frozen):
    schema_name: str
    bodies: list[StepBody]


GeoKind = Literal["point", "line", "arc", "circle"]
ConstraintKind = Literal[
    "coincident",
    "horizontal",
    "vertical",
    "tangent",
    "point_on_object",
    "radius",
    "diameter",
    "distance",
    "distance_x",
    "distance_y",
    "angle",
]


class Constraint(Frozen):
    kind: ConstraintKind
    refs: list[str]
    value: float | None = None
    expr: str | None = None


class SketchGeo(Frozen):
    name: str
    kind: GeoKind
    values: list[float]


class SketchDof(Frozen):
    part: str
    sketch: str
    geometry: list[SketchGeo]
    unknowns: int
    constraints: list[Constraint]
    redundant: int
    dof: int | None
    solve_error: float = 0.0
    note: str = ""


class FeatureEntry(Frozen):
    part: str
    id: str
    name: str
    kind: str
    depends_on: list[str]


class Bundle(Frozen):
    title: str
    design_hash: str
    design: Design
    features: list[FeatureEntry]
    sketches: list[SketchDof]
    files: list[str]
