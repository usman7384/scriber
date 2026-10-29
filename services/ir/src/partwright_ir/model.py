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
    fastener: str | None = Field(default=None, description="metric screw or thread, e.g. M6 or M18x1.5")
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


class AirfoilSection(FeatureBase):
    kind: Literal["airfoil_section"]
    plane: PlaneRef
    naca: str = Field(pattern=r"^\d{4}$", description="NACA 4-digit code, e.g. 2412")
    chord: Expr
    leading_edge: Point = (0.0, 0.0)
    twist: Expr = Field(default=0.0, description="degrees, leading edge up, about the leading edge")


class Loft(FeatureBase):
    kind: Literal["loft"]
    sections: list[str] = Field(min_length=2, description="airfoil_section ids in order")
    ruled: bool = False


class SpurGear(FeatureBase):
    kind: Literal["spur_gear"]
    plane: PlaneRef = PlaneRef()
    center: Point = (0.0, 0.0)
    module: Expr
    teeth: Expr
    face_width: Expr
    pressure_angle: Expr = 20.0
    backlash: Expr = Field(default=0.0, description="circular backlash of a pair that both carry it; each tooth is thinned by half")
    bore: Expr | None = None
    hub_diameter: Expr | None = None
    hub_length: Expr | None = None


class Rib(FeatureBase):
    kind: Literal["rib"]
    plane: PlaneRef = Field(description="the face the rib stands on; it grows along the face's outward normal")
    start: Point
    end: Point
    thickness: Expr
    height: Expr


class BossPattern(FeatureBase):
    kind: Literal["boss_pattern"]
    plane: PlaneRef
    at: Placement
    diameter: Expr
    height: Expr
    hole_diameter: Expr | None = Field(default=None, description="pilot or insert hole from the boss top")
    hole_depth: Expr | None = Field(default=None, description="defaults to the boss height")


class ShellWithLid(FeatureBase):
    kind: Literal["shell_with_lid"]
    width: Expr
    depth: Expr
    height: Expr
    wall: Expr
    floor: Expr
    lid_thickness: Expr
    lip_height: Expr
    clearance: Expr = 0.2
    screw: str | None = Field(default="M3", description="corner screws, e.g. M3; null for no bosses")
    boss_diameter: Expr | None = Field(default=None, description="defaults to 2.5 x the screw size")


class Lid(FeatureBase):
    kind: Literal["lid"]
    of: str = Field(description="id of the part whose shell_with_lid this lid closes")


class Keyway(FeatureBase):
    kind: Literal["keyway"]
    of: str = Field(description="the extrude, revolve or hole that made the shaft or bore")
    on: Literal["shaft", "bore"] = "shaft"
    position: Expr = Field(default=0.0, description="from the surface's -x/-y/-z end along its axis")
    length: Expr | None = Field(default=None, description="null runs the full surface length")
    width: Expr | None = Field(default=None, description="null takes DIN 6885 from the diameter")
    depth: Expr | None = Field(default=None, description="null takes DIN 6885 t1 (shaft) or t2 (bore)")
    angle: Expr = Field(default=0.0, description="about the axis, from +z (or +x for a z axis)")


class Groove(FeatureBase):
    kind: Literal["groove"]
    of: str = Field(description="the extrude, revolve or hole that made the shaft or bore")
    on: Literal["shaft", "bore"] = "shaft"
    position: Expr = Field(description="from the surface's -x/-y/-z end along its axis to the groove's near side")
    width: Expr
    depth: Expr


HIGH_LEVEL = (SpurGear, Rib, BossPattern, ShellWithLid, Lid, Keyway, Groove)
Feature = Annotated[
    Extrude
    | Revolve
    | Hole
    | Pattern
    | Fillet
    | Chamfer
    | Shell
    | AirfoilSection
    | Loft
    | SpurGear
    | Rib
    | BossPattern
    | ShellWithLid
    | Lid
    | Keyway
    | Groove,
    Field(discriminator="kind"),
]


class FaceGroup(Frozen):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", description="e.g. mount_face, load_face")
    faces: Selector


class Part(Frozen):
    id: str
    name: str
    material: str | None = None
    process: Process = "any"
    datums: list[Datum] = []
    sketches: list[Sketch]
    features: list[Feature] = Field(min_length=1)
    face_groups: list[FaceGroup] = Field(default=[], description="named faces for simulation and downstream tools")


class Connector(Frozen):
    id: str
    part: str
    origin: Point3 = (0.0, 0.0, 0.0)
    z: Direction = Field(default="+z", description="mating axis, in the part's own coordinates")
    x: Direction = Field(default="+x", description="perpendicular to z; fixes the rotation about it")


class Joint(Frozen):
    id: str
    parent: str = Field(description="connector id on the part that stays")
    child: str = Field(description="connector id on the part placed so its connector meets the parent's")
    kind: Literal["fastened", "revolute", "slider"] = "fastened"
    angle: Expr = Field(default=0.0, description="rotation of the child about the parent connector's z, deg")
    offset: Expr = Field(default=0.0, description="shift of the child along the parent connector's z")


class Assembly(Frozen):
    connectors: list[Connector] = []
    joints: list[Joint] = []


class Design(Frozen):
    ir_version: Literal[2] = 2
    title: str = Field(max_length=60)
    params: list[Param]
    parts: list[Part] = Field(min_length=1)
    assembly: Assembly | None = None

    @model_validator(mode="before")
    @classmethod
    def _upgrade(cls, data: Any) -> Any:
        return upgrade_v1(data) if isinstance(data, dict) else data

    def param_values(self) -> dict[str, float]:
        return {p.name: p.value for p in self.params}
