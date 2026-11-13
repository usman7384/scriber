from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scriber_ir.upgrade import upgrade_v1

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
    fit: str | None = Field(
        default=None, description="ISO 286 tolerance class as written on a drawing, e.g. H7 for a bore or g6 for a shaft"
    )
    tol_plus: float | None = Field(default=None, description="upper deviation, e.g. 0.05 for +0.05")
    tol_minus: float | None = Field(default=None, description="lower deviation, e.g. -0.02; with tol_plus 0.02 it is +-0.02")
    reference: bool = Field(
        default=False,
        description="a dimension stated for information only, such as a drawing's (60) or a true arc radius; it need not drive a feature",
    )


class PlaneRef(Frozen):
    ref: str = Field(default="XY", description="XY, XZ, YZ, a datum id, or '<feature id>.<face>' / 'part.<face>'")
    offset: Expr = 0.0


class Datum(Frozen):
    id: str
    base: BasePlane = "XY"
    offset: Expr = 0.0
    rotate_about: Literal["none", "x", "y"] = "none"
    angle: Expr = 0.0
    origin: Point3 | None = Field(default=None, description="with normal: a plane in any orientation; base, offset, rotation ignored")
    normal: Point3 | None = None
    x_dir: Point3 | None = Field(default=None, description="sketch x direction on that plane; any vector across the normal")


class Selector(Frozen):
    of: str = "part"
    meets: str | None = Field(default=None, description="only edges or faces where 'of' joins this feature, e.g. a boss and its plate")
    normal: Literal["any", "+x", "-x", "+y", "-y", "+z", "-z"] | Point3 = Field(default="any", description="an axis name or a vector")
    parallel: Literal["any", "x", "y", "z"] | Point3 = Field(default="any", description="an axis name or a vector")
    convexity: Literal["any", "concave", "convex"] = "any"
    extreme: Literal["any", "max", "min"] = "any"
    geom: Literal["any", "line", "circle"] = Field(default="any", description="edges only: straight lines, or circles and arcs")
    arc_radius: Expr | None = Field(default=None, description="edges only: circles and arcs of this radius, e.g. the outer rim")
    outline: bool = Field(
        default=False, description="edges only, with a normal: just the outer boundary of those flat faces, not hole or pocket edges"
    )


class Rect(Frozen):
    kind: Literal["rect"]
    center: Point = (0.0, 0.0)
    width: Expr
    height: Expr
    corner_radius: Expr = 0.0
    angle: Expr = Field(default=0.0, description="deg, counter-clockwise about the centre")
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


class Ellipse(Frozen):
    kind: Literal["ellipse"]
    center: Point = (0.0, 0.0)
    width: Expr
    height: Expr
    angle: Expr = 0.0
    subtract: bool = False


class Spline(Frozen):
    kind: Literal["spline"]
    points: list[Point] = Field(min_length=3, description="a closed smooth outline through these points, in order")
    subtract: bool = False


class Segment(Frozen):
    to: Point
    arc: Literal["none", "cw", "ccw"] = "none"
    radius: Expr | None = None
    center: Point | None = Field(default=None, description="arcs only: the arc's centre instead of a radius; any sweep up to a full turn")
    fillet: Expr = 0.0


class Path(Frozen):
    kind: Literal["path"]
    start: Point
    segments: list[Segment] = Field(min_length=2)
    subtract: bool = False


Entity = Annotated[Rect | Circle | Polygon | Slot | Path | Ellipse | Spline, Field(discriminator="kind")]


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
    wrap: str | None = Field(
        default=None,
        description="id of an earlier feature whose cylinder the sketch wraps onto; the sketch plane touches it; "
        "lengths keep along the surface and depth is radial",
    )


class Revolve(FeatureBase):
    kind: Literal["revolve"]
    sketch: str
    axis: Literal["X", "Y"] = Field(default="Y", description="the sketch's own x or y axis, shifted by axis_offset")
    axis_offset: Expr = 0.0
    angle: Expr = Field(
        default=360.0, description="deg, right-handed about the axis's positive direction; a partial revolve starts at the sketch"
    )
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
    through: Literal["all", "next"] = Field(
        default="all",
        description="with depth null: 'all' cuts the whole part both ways; 'next' stops past the first wall, as THRU on a drawing",
    )
    drill_point: Literal["flat", "118"] = "flat"
    cb_diameter: Expr | None = None
    cb_depth: Expr | None = None
    cs_diameter: Expr | None = None
    cs_angle: Expr = 90.0
    thread: str | None = None
    thread_depth: Expr | None = Field(default=None, description="tapped: the threaded length when it is shorter than the drill depth")


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


class Draft(FeatureBase):
    kind: Literal["draft"]
    faces: Selector = Field(description='the side faces to taper, e.g. {"of": "blade", "normal": "+x"}')
    neutral: PlaneRef = Field(default=PlaneRef(), description="the plane where the faces keep their size, usually the parting line")
    angle: Expr = Field(description="deg; positive tapers the faces inward away from the neutral plane")


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
    sections: list[str] = Field(min_length=2, description="airfoil_section ids or sketch ids, in order along the loft")
    ruled: bool = False
    mode: Literal["add", "cut", "intersect"] = "add"
    wall: Expr | None = Field(default=None, description="hollow skin of this thickness, open at the end sections")


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
    boss_diameter: Expr | None = Field(default=None, description="defaults to 2.5 x the screw size, or 3 x its pilot hole if larger")


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


class Thread(FeatureBase):
    kind: Literal["thread"]
    of: str = Field(description="the extrude, revolve or hole that made the shaft or bore")
    on: Literal["shaft", "bore"] = "shaft"
    designation: str = Field(description="metric thread such as M110x4 or M12x1.25; a shaft is its major diameter, a bore its tap drill")
    position: Expr = Field(default=0.0, description="from the surface's -x/-y/-z end along its axis")
    length: Expr | None = Field(default=None, description="null runs the full surface length")
    modelled: bool = Field(default=False, description="true cuts the helical thread form; false records a cosmetic thread, as drawings do")


class Tube(FeatureBase):
    kind: Literal["tube"]
    points: list[Point3] = Field(min_length=2, description="centre line through these points in part coordinates")
    outer_diameter: Expr
    wall: Expr | None = Field(default=None, description="null for a solid rod")
    bend_radius: Expr = Field(default=0.0, description="rounds the corners of the centre line")
    mode: Literal["add", "cut"] = "add"


class Bend(Frozen):
    line: tuple[Point, Point] = Field(description="the bend line on the flat pattern, through two points")
    angle: Expr = Field(default=90.0, description="deg the far side turns; 90 makes a right-angle flange")
    direction: Literal["up", "down"] = Field(default="up", description="up folds toward +z of the flat, as BEND UP on a drawing")
    radius: Expr | None = Field(default=None, description="inside radius; null uses the part's bend_radius")
    relief: Expr | None = Field(
        default=None, description="width of the relief slots cut at both ends of a bend that stops inside the outline"
    )


class Flange(Frozen):
    edge: tuple[Point, Point] = Field(description="an outline edge of the flat pattern, end to end")
    length: Expr = Field(description="the straight leg beyond the bend")
    angle: Expr = Field(default=90.0, description="deg; 180 with a small radius makes a hem")
    direction: Literal["up", "down"] = "up"
    radius: Expr | None = Field(default=None, description="inside radius; null uses the part's bend_radius")


class SheetMetal(FeatureBase):
    kind: Literal["sheet_metal"]
    sketch: str = Field(description="the flat pattern, holes and cut-outs included; its largest panel stays put")
    thickness: Expr
    bend_radius: Expr = Field(description="inside bend radius")
    k_factor: Expr = Field(default=0.33, description="neutral axis position across the thickness")
    bends: list[Bend] = []
    flanges: list[Flange] = Field(default=[], description="legs added on outline edges, folded like bends; the flat pattern grows to suit")


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
    | Groove
    | Tube
    | SheetMetal
    | Draft
    | Thread,
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
    z: Direction | Point3 = Field(default="+z", description="mating axis in the part's own coordinates: an axis name or any vector")
    x: Direction | Point3 = Field(default="+x", description="perpendicular to z; fixes the rotation about it")


class Joint(Frozen):
    id: str
    parent: str = Field(description="connector id on the part that stays")
    child: str = Field(description="connector id on the part placed so its connector meets the parent's")
    kind: Literal["fastened", "revolute", "slider", "spherical"] = "fastened"
    angle: Expr = Field(default=0.0, description="rotation of the child about the parent connector's z, deg")
    offset: Expr = Field(default=0.0, description="shift of the child along the parent connector's z")


class Instance(Frozen):
    id: str = Field(description="a further copy of a part, placed by its own connectors and joints like a part")
    part: str
    mirror: Literal["none", "XY", "XZ", "YZ"] = Field(default="none", description="mirror across a base plane, e.g. XZ for the other side")


class Assembly(Frozen):
    connectors: list[Connector] = []
    joints: list[Joint] = Field(default=[], description="a joint whose child is already placed closes a loop and is only checked")
    instances: list[Instance] = []


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
