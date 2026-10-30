from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from partwright_context import KbStats
from partwright_geometry import FaceMesh, Finding
from partwright_ir import Design, DesignDiff, Process, Provenance, RuleKind

JobKind = Literal["generate", "refine", "edit", "params", "ingest", "batch", "build"]
JobStatus = Literal["queued", "running", "done", "failed"]
Origin = Literal[
    "generate", "refine", "edit", "params", "restore", "context", "variant", "suggestion", "design", "sizing", "fork", "material"
]
FileKind = Literal["step", "stl", "glb", "py", "ir"]
ExportKind = Literal["step", "stl", "glb", "py", "ir", "fcstd"]
HookEvent = Literal["version.created", "job.failed", "version.stale"]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Project(Frozen):
    id: str
    name: str
    created: str
    model_count: int
    file_count: int


class File(Frozen):
    id: str
    project_id: str
    name: str
    kind: str | None
    role: str | None
    status: Literal["processing", "processed", "failed"]
    error: str | None = None
    facts: int = 0
    rules: int = 0
    uploaded: str
    used_in: list[str] = []


class Fact(Frozen):
    id: str
    file_id: str
    kind: str
    name: str
    value: float | str
    unit: str
    tol: tuple[float, float] | None = None
    count: int | None = None
    page: int
    line: int
    text: str
    ref: str | None


class Rule(Frozen):
    id: str
    kind: RuleKind
    value: float
    unit: Literal["mm", "deg", ""]
    process: Process = "any"
    severity: Literal["error", "warning"] = "error"
    binding: Literal["static", "dynamic"] = "static"
    text: str = ""
    source_ref: str | None = None


class Param(Frozen):
    name: str
    label: str
    value: float
    unit: str
    min: float | None = None
    max: float | None = None
    description: str
    provenance: Provenance


class Check(Frozen):
    description: str
    passed: bool
    actual: str


class Input(Frozen):
    kind: Literal["prompt", "file"]
    role: Literal["used", "unused"]
    id: str | None = None
    name: str | None = None


class Metrics(Frozen):
    bbox: tuple[float, float, float]
    volume: float
    mass_g: float | None
    holes: int


class VersionData(Frozen):
    created: str
    status: Literal["ok", "failed"]
    origin: Origin
    prompt: str | None = None
    process: Process = "any"
    params: list[Param] = []
    checks: list[Check] = []
    findings: list[Finding] = []
    metrics: Metrics | None = None
    attachments: list[str] = []
    inputs: list[Input] = []
    used: list[str] = []
    thumbnail: bool = False
    changes: DesignDiff | None = None


class Version(Frozen):
    model_id: str
    number: int
    created: str
    status: Literal["ok", "failed"]
    origin: Origin
    prompt: str | None
    params: list[Param]
    checks: list[Check]
    findings: list[Finding]
    metrics: Metrics | None
    files: dict[FileKind, str]
    thumbnail_url: str | None
    attachments: list[str]
    inputs: list[Input]
    changes: DesignDiff | None


class ForkSource(Frozen):
    publication: str
    model_id: str
    version: int
    title: str
    author: str


class Model(Frozen):
    id: str
    project_id: str
    title: str
    created: str
    latest_version: int | None
    versions: int
    thumbnail_url: str | None
    stale: bool = False
    forked_from: ForkSource | None = None


class ModelDetail(Model):
    version: Version | None


class MaterialOut(Frozen):
    name: str
    density_g_cm3: float
    youngs_modulus_gpa: float
    yield_mpa: float
    source: str


class Component(Frozen):
    id: str
    name: str
    material: str | None
    properties: MaterialOut | None = None
    parent: str | None
    joint: str | None


class Step(Frozen):
    kind: str
    message: str
    attempt: int
    elapsed_ms: int
    progress: int = 0
    thumbnail_url: str | None = None


class Job(Frozen):
    id: str
    kind: JobKind
    status: JobStatus
    project_id: str
    model_id: str | None = None
    version: int | None = None
    error: str | None = None
    created: str
    started: str | None = None
    finished: str | None = None
    request: dict[str, JsonValue] | None = None
    steps: list[Step] = []


class GraphNode(Frozen):
    id: str
    type: str
    name: str


class GraphEdge(Frozen):
    src: str
    dst: str
    type: str


class GraphView(Frozen):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    counts: dict[str, int]


class ProjectIn(Frozen):
    name: str = Field(min_length=1, max_length=120)


class GenerateIn(Frozen):
    prompt: str = Field(min_length=1)
    process: Process = "any"
    context_ids: list[str] | None = None
    attachments: list[str] = []
    thinking: Literal["low", "high"] | None = None


class RefineIn(Frozen):
    instruction: str = Field(min_length=1)
    target: str | None = None
    process: Process | None = None
    attachments: list[str] = []


class ParamsIn(Frozen):
    values: dict[str, float] = Field(min_length=1)


class BatchIn(Frozen):
    project_id: str
    prompts: list[str] = Field(min_length=1, max_length=1000)
    process: Process = "any"


class Batch(Frozen):
    jobs: list[Job]


class VariantsIn(Frozen):
    instruction: str | None = Field(default=None, min_length=1)
    param: str | None = None
    values: list[float] = Field(default=[], max_length=1000)


class SuggestionOut(Frozen):
    id: str
    target: str
    change: dict[str, float]
    rationale: str
    status: Literal["open", "accepted", "ignored"] = "open"


class ShareIn(Frozen):
    model_id: str
    version: int | None = None


class Share(Frozen):
    id: str
    url: str


class HookIn(Frozen):
    url: str = Field(pattern=r"^https?://")
    events: list[HookEvent] = Field(min_length=1)


class Hook(Frozen):
    id: str
    url: str
    events: list[HookEvent]


class TokenIn(Frozen):
    name: str = Field(min_length=1, max_length=120)


class Token(Frozen):
    id: str
    name: str
    created: str


class NewToken(Token):
    token: str


class Tools(Frozen):
    freecad: bool
    prusaslicer: bool


class Health(Frozen):
    status: str
    model: str
    ollama: bool
    tools: Tools


class Printability(Frozen):
    model_id: str
    version: int
    ok: bool
    exit_code: int
    manifold: bool
    layers: int
    gcode_bytes: int
    warnings: list[str]
    errors: list[str]


class ContextListing(Frozen):
    files: list[File]
    stats: KbStats
    stale: list[str]


class GenerateV1(Frozen):
    prompt: str = Field(min_length=1)
    image: str | None = None
    mesh: str | None = None


class ModifyV1(Frozen):
    model_id: str
    prompt: str = Field(min_length=1)
    attachments: list[str] = []


class EditV1(Frozen):
    model_id: str
    component_id: str
    params: dict[str, float] = Field(min_length=1)


class DownloadV1(Frozen):
    model_id: str
    format: Literal["glb", "step", "stl"]


class JobRef(Frozen):
    job_id: str


class DesignIn(Frozen):
    design: Design
    prompt: str | None = None


class MaterialIn(Frozen):
    material: str = Field(min_length=1)
    part: str | None = None


class Usage(Frozen):
    user: str
    generations: int
    limit: int | None


class BugIn(Frozen):
    model_id: str
    version: int
    text: str = Field(min_length=1, max_length=10_000)
    screenshot: str | None = Field(default=None, description="data URL of a PNG or JPEG")


class Bug(Frozen):
    id: str
    model_id: str
    version: int
    text: str
    user: str
    created: str
    screenshot_url: str | None


class PublishIn(Frozen):
    model_id: str
    version: int | None = None


class Publication(Frozen):
    id: str
    model_id: str
    version: int
    title: str
    author: str
    created: str
    thumbnail_url: str | None


class ForkIn(Frozen):
    project_id: str


class Sensitivity(Frozen):
    name: str
    value: float
    unit: str
    step: float
    d: dict[str, float | None]
    error: str | None = None


class Sensitivities(Frozen):
    model_id: str
    version: int
    metrics: dict[str, float | None]
    params: list[Sensitivity]


class FaceStress(Frozen):
    face_group: str
    max_stress_mpa: float
    allowable_mpa: float = Field(gt=0)


class SimulationIn(Frozen):
    solver: str = ""
    load_case: str = ""
    results: list[FaceStress] = Field(min_length=1)


class FeatureNode(Frozen):
    id: str
    name: str
    kind: str
    intent: str
    params: list[str] = Field(description="parameters this feature's expressions use, in design order")
    faces: list[int] = Field(description="indices into the part's faces that this feature made")


class PartTree(Frozen):
    id: str
    name: str
    features: list[FeatureNode]
    faces: list[FaceMesh] = Field(description="the part's faces in assembly coordinates, mm, Z up")
    explode: tuple[float, float, float] | None = Field(
        description="unit joint axis the part slides along when exploded; none for a root part"
    )


class Structure(Frozen):
    parts: list[PartTree]
