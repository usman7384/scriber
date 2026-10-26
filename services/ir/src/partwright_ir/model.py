from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Expr = float | str
Point = tuple[Expr, Expr]


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


class SketchPlane(Frozen):
    base: Literal["XY", "XZ", "YZ"] = "XY"
    offset: Expr = 0.0


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


Entity = Annotated[Rect | Circle | Polygon | Slot, Field(discriminator="kind")]


class Sketch(Frozen):
    id: str
    plane: SketchPlane = SketchPlane()
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
    distance: Expr
    mode: Literal["add", "cut"] = "add"
    symmetric: bool = False


class Revolve(FeatureBase):
    kind: Literal["revolve"]
    sketch: str
    axis: Literal["X", "Y"] = "Y"
    angle: Expr = 360.0
    mode: Literal["add", "cut"] = "add"


class Hole(FeatureBase):
    kind: Literal["hole"]
    plane: SketchPlane
    at: Placement
    diameter: Expr
    depth: Expr | None = None
    counterbore_diameter: Expr | None = None
    counterbore_depth: Expr | None = None


EdgeSet = Literal["all", "top", "bottom", "parallel_x", "parallel_y", "parallel_z"]


class Fillet(FeatureBase):
    kind: Literal["fillet"]
    edges: EdgeSet
    radius: Expr


class Chamfer(FeatureBase):
    kind: Literal["chamfer"]
    edges: EdgeSet
    length: Expr


class Shell(FeatureBase):
    kind: Literal["shell"]
    open_face: Literal["top", "bottom", "none"] = "top"
    thickness: Expr


Feature = Annotated[Extrude | Revolve | Hole | Fillet | Chamfer | Shell, Field(discriminator="kind")]


class Part(Frozen):
    id: str
    name: str
    material: str | None = None
    sketches: list[Sketch] = Field(min_length=1)
    features: list[Feature] = Field(min_length=1)


class Design(Frozen):
    title: str = Field(max_length=60)
    params: list[Param]
    parts: list[Part] = Field(min_length=1)

    def param_values(self) -> dict[str, float]:
        return {p.name: p.value for p in self.params}
