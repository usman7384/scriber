from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from partwright_ir.upgrade import upgrade_v1

Expr = float | str
Point = tuple[Expr, Expr]
Point3 = tuple[Expr, Expr, Expr]
BasePlane = Literal["XY", "XZ", "YZ"]
Direction = Literal["+x", "-x", "+y", "-y", "+z", "-z"]
Process = Literal["any", "milling_3axis", "turning", "fdm", "sla", "sls", "injection", "casting", "sheet_metal"]
FACE_NAMES = ("top", "bottom", "front", "back", "left", "right", "start", "end", "+x", "-x", "+y", "-y", "+z", "-z")


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Provenance(Frozen):
    source: Literal["prompt", "document", "rule", "standard", "default", "user_edit", "mesh_fit", "vision"]
    ref: str | None = None
    quote: str | None = None


class Param(Frozen):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    value: float
    unit: Literal["mm", "deg", ""]
    min: float | None = None
    max: float | None = None
    description: str = ""
    provenance: Provenance = Provenance(source="default")


class PlaneRef(Frozen):
    ref: str = Field(default="XY", description="XY, XZ, YZ, a datum id, or '<feature id>.<face>' / 'part.<face>'")
    offset: Expr = 0.0


class Datum(Frozen):
    id: str
    base: BasePlane = "XY"
    offset: Expr = 0.0
    rotate_about: Literal["none", "x", "y"] = "none"
    angle: Expr = 0.0


class Selector(Frozen):
    of: str = "part"
    normal: Literal["any", "+x", "-x", "+y", "-y", "+z", "-z"] = "any"
    parallel: Literal["any", "x", "y", "z"] = "any"
    convexity: Literal["any", "concave", "convex"] = "any"
    extreme: Literal["any", "max", "min"] = "any"


class Rect(Frozen):
    kind: Literal["rect"]
    center: Point = (0.0, 0.0)
    width: Expr
    height: Expr
    corner_radius: Expr = 0.0
    subtract: bool = False


class Circle(Frozen):
    kind: Literal["circle"]
    center: Point = (0.0, 0.0)
    diameter: Expr
    subtract: bool = False


class Polygon(Frozen):
    kind: Literal["polygon"]
    points: list[Point] = Field(min_length=3)
    subtract: bool = False


class Slot(Frozen):
    kind: Literal["slot"]
    center: Point = (0.0, 0.0)
    length: Expr
    width: Expr
    angle: Expr = 0.0
    subtract: bool = False


class Segment(Frozen):
    to: Point
    arc: Literal["none", "cw", "ccw"] = "none"
    radius: Expr | None = None
    fillet: Expr = 0.0


class Path(Frozen):
    kind: Literal["path"]
    start: Point
    segments: list[Segment] = Field(min_length=2)
    subtract: bool = False


Entity = Annotated[Rect | Circle | Polygon | Slot | Path, Field(discriminator="kind")]


class Sketch(Frozen):
    id: str
    plane: PlaneRef = PlaneRef()
    entities: list[Entity] = Field(min_length=1)


class GridPattern(Frozen):
    kind: Literal["grid"]
    center: Point = (0.0, 0.0)
    count_x: Expr
    count_y: Expr
    spacing_x: Expr
    spacing_y: Expr


class PolarPattern(Frozen):
    kind: Literal["polar"]
    center: Point = (0.0, 0.0)
    count: Expr
    diameter: Expr
    start_angle: Expr = 0.0


class PointList(Frozen):
    kind: Literal["points"]
    points: list[Point] = Field(min_length=1)


Placement = Annotated[GridPattern | PolarPattern | PointList, Field(discriminator="kind")]


class FeatureBase(Frozen):
    id: str
    name: str
    intent: str = ""
    provenance: Provenance = Provenance(source="prompt")


class Extrude(FeatureBase):
    kind: Literal["extrude"]
    sketch: str
    mode: Literal["add", "cut", "intersect"] = "add"
    extent: Literal["blind", "symmetric", "two_sided", "through_all", "up_to_next"] = "blind"
    distance: Expr | None = None
    distance2: Expr | None = None
    taper: Expr = 0.0


class Revolve(FeatureBase):
    kind: Literal["revolve"]
    sketch: str
    axis: Literal["X", "Y"] = "Y"
    axis_offset: Expr = 0.0
    angle: Expr = 360.0
    mode: Literal["add", "cut", "intersect"] = "add"


class Hole(FeatureBase):
    kind: Literal["hole"]
    plane: PlaneRef
    at: Placement
    type: Literal["simple", "counterbore", "countersink", "tapped"] = "simple"
    fastener: str | None = Field(default=None, pattern=r"^M\d+(\.\d)?$")
    fit: Literal["close", "normal", "loose"] = "normal"
    diameter: Expr | None = None
    depth: Expr | None = None
    drill_point: Literal["flat", "118"] = "flat"
    cb_diameter: Expr | None = None
    cb_depth: Expr | None = None
    cs_diameter: Expr | None = None
    cs_angle: Expr = 90.0
    thread: str | None = None


class Pattern(FeatureBase):
    kind: Literal["pattern"]
    features: list[str] = Field(min_length=1)
    type: Literal["linear", "polar", "mirror"]
    count: Expr = 2
    direction: Literal["x", "y", "z"] = "x"
    spacing: Expr | None = None
    axis: Literal["x", "y", "z"] = "z"
    center: Point3 = (0.0, 0.0, 0.0)
    angle: Expr = 360.0
    mirror_plane: BasePlane = "YZ"


class Fillet(FeatureBase):
    kind: Literal["fillet"]
    edges: Selector
    radius: Expr


class Chamfer(FeatureBase):
    kind: Literal["chamfer"]
    edges: Selector
    length: Expr
    length2: Expr | None = None


class Shell(FeatureBase):
    kind: Literal["shell"]
    thickness: Expr
    open: list[Selector] = []


Feature = Annotated[Extrude | Revolve | Hole | Pattern | Fillet | Chamfer | Shell, Field(discriminator="kind")]


class Part(Frozen):
    id: str
    name: str
    material: str | None = None
    process: Process = "any"
    datums: list[Datum] = []
    sketches: list[Sketch] = Field(min_length=1)
    features: list[Feature] = Field(min_length=1)


class Design(Frozen):
    ir_version: Literal[2] = 2
    title: str = Field(max_length=60)
    params: list[Param]
    parts: list[Part] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _upgrade(cls, data: Any) -> Any:
        return upgrade_v1(data) if isinstance(data, dict) else data

    def param_values(self) -> dict[str, float]:
        return {p.name: p.value for p in self.params}
