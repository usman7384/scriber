from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from partwright_ir import Design, Provenance, Rule, ShapeDescriptor

FileKind = Literal["pdf", "docx", "md", "txt", "csv", "xlsx", "xml", "yaml", "image", "step", "stl", "obj"]
FactKind = Literal["parameter", "tolerance", "holes", "hole", "material", "standard"]
NodeType = Literal["document", "chunk", "fact", "rule", "standard", "entity", "part", "feature", "parameter"]
EdgeType = Literal["contains", "defines", "mentions", "related_to", "constrains", "derived_from", "used_in"]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Document(Frozen):
    id: str
    name: str
    kind: FileKind
    role: Literal["spec", "convention"] = "spec"
    status: Literal["processed"] = "processed"
    sha256: str
    pages: int
    chunks: int
    facts: int
    rules: int
    descriptor: ShapeDescriptor | None = None


class Chunk(Frozen):
    id: str
    doc_id: str
    page: int
    line_start: int
    line_end: int
    text: str

    @property
    def ref(self) -> str:
        return f"{self.doc_id}#p{self.page}:l{self.line_start}"


class Fact(Frozen):
    id: str
    doc_id: str
    kind: FactKind
    name: str
    value: float | str
    unit: str = ""
    tol: tuple[float, float] | None = Field(default=None, description="lower and upper deviation")
    count: int | None = None
    at: tuple[float, float] | None = None
    page: int
    line: int
    text: str
    source: Provenance


class ProposedFact(Frozen):
    name: str
    value: float
    unit: str = ""
    quote: str


class PartRef(Frozen):
    id: str
    name: str
    origin: Literal["uploaded", "generated"]
    model_id: str | None = None
    doc_id: str | None = None
    descriptor: ShapeDescriptor | None = None
    design: Design | None = None
    score: float


class ContextPack(Frozen):
    query: str
    chunks: list[Chunk]
    facts: list[Fact]
    rules: list[Rule]
    similar_parts: list[PartRef]
    conventions: list[Fact]


class GraphNode(Frozen):
    id: str
    type: NodeType
    name: str
    doc_id: str | None = None
    model_id: str | None = None
    props: dict[str, JsonValue] = Field(default_factory=dict)


class GraphEdge(Frozen):
    src: str
    dst: str
    type: EdgeType


class GraphView(Frozen):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    counts: dict[str, int]


class KbStats(Frozen):
    files: int
    facts: int
    rules: int
    entities: int
    relations: int
    generations: int
    used_in_generation: int
    score: int
    level: int
    next_level_score: int
