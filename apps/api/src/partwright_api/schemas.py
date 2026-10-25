from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from partwright_context import KbStats
from partwright_geometry import Finding
from partwright_ir import DesignDiff, Process, Provenance, RuleKind

JobKind = Literal["generate", "refine", "edit", "params", "ingest", "batch"]
JobStatus = Literal["queued", "running", "done", "failed"]
Origin = Literal["generate", "refine", "edit", "params", "restore"]
FileKind = Literal["step", "stl", "glb", "py", "ir"]
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
    changes: DesignDiff | None


class Model(Frozen):
    id: str
    project_id: str
    title: str
    created: str
    latest_version: int | None
    versions: int
    thumbnail_url: str | None
    stale: bool = False


class ModelDetail(Model):
    version: Version | None


class Step(Frozen):
    kind: str
    message: str
    attempt: int
    elapsed_ms: int
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


class Health(Frozen):
    status: str
    model: str
    ollama: bool


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
