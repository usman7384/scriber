import ast
import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from partwright_geometry.freecad import FreeCadError, alias, run_freecad
from partwright_geometry.models import Constraint, SketchFrame
from partwright_geometry.onshape_export import UnsupportedExportError
from partwright_geometry.sketcher import analyse_sketch
from partwright_ir import Design, evaluate
from partwright_ir.expr import names, parse
from partwright_ir.fasteners import hole_size
from partwright_ir.model import Circle, Expr, Extrude, GridPattern, Hole, Part, PlaneRef, Point, PointList, Sketch

Json = dict[str, Any]
Values = dict[str, float]
Extrudes = dict[str, tuple[Extrude, SketchFrame]]
BASE_PLANES = ("XY", "XZ", "YZ")
POSITION = {"start": 1, "end": 2, "center": 3}
SKETCHER = {
    "coincident": "Coincident",
    "horizontal": "Horizontal",
    "vertical": "Vertical",
    "tangent": "Tangent",
    "point_on_object": "PointOnObject",
    "radius": "Radius",
    "diameter": "Diameter",
    "distance": "Distance",
    "distance_x": "DistanceX",
    "distance_y": "DistanceY",
    "angle": "Angle",
}
OPERATORS: dict[type[ast.operator], str] = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}
# FreeCAD's trigonometry takes unitless arguments in degrees, as the IR does
FUNCTIONS = ("sin", "cos", "tan", "sqrt")
SHEET = "Parameters"
ALIASES = {"top": "+z", "bottom": "-z", "front": "-y", "back": "+y", "left": "-x", "right": "+x"}
AXIS_FACES = {f"{sign}{axis}": (i, 1 if sign == "+" else -1) for i, axis in enumerate("xyz") for sign in "+-"}


def export_fcstd(design: Design, frames: list[SketchFrame], freecad: Path, out: Path) -> Path:
    errors = run_freecad(freecad, "fcstd_write.FCMacro", fcstd_plan(design, frames) | {"out": str(out)})["errors"]
    if errors:
        raise FreeCadError(f"FreeCAD could not rebuild {design.title!r}: {'; '.join(errors)}")
    return out


def fcstd_plan(design: Design, frames: list[SketchFrame]) -> Json:
    if design.assembly is not None:
        raise UnsupportedExportError("assembly joints and placements have no FreeCAD export yet")
    values = design.param_values()
    planes = iter(frames)
    params = [{"name": p.name, "alias": alias(p.name), "value": p.value} for p in design.params]
    return {"params": params, "bodies": [_body(part, planes, values) for part in design.parts]}


def _body(part: Part, planes: Iterator[SketchFrame], values: Values) -> Json:
    sketches = {s.id: s for s in part.sketches}
    objects: list[Json] = []
    extrudes: Extrudes = {}
    for f in part.features:
        match f:
            case Extrude():
                sketch, frame = sketches[f.sketch], next(planes)
                placement = _placement(sketch.plane, frame, extrudes, values)
                objects += [_sketch(part.id, f"{f.id}_sketch", sketch, frame, placement, values), _extrude(f, frame, values)]
                extrudes[f.id] = (f, frame)
            case Hole():
                sketch, frame = _hole_sketch(f, values), next(planes)
                placement = _placement(sketch.plane, frame, extrudes, values)
                objects += [_sketch(part.id, f"{f.id}_sketch", sketch, frame, placement, values), _hole(f, frame, values)]
            case _:
                raise UnsupportedExportError(f"{f.kind} feature {f.id!r} has no FreeCAD export yet")
    return {"name": f"{part.id}_body", "label": part.name, "objects": objects}


def _sketch(part: str, name: str, sketch: Sketch, frame: SketchFrame, placement: dict[str, str], values: Values) -> Json:
    found = analyse_sketch(part, sketch, values, 0)
    if found.dof != 0:
        raise UnsupportedExportError(f"sketch {sketch.id!r} is not fully constrained ({found.note or f'{found.dof} DOF'})")
    index = {g.name: i for i, g in enumerate(found.geometry)}
    constraints = _endpoint_tangents(found.constraints)
    expressions = {f"Constraints[{i}]": e for i, c in enumerate(constraints) if (e := _expr(c.expr, c.kind))}
    return {
        "type": "Sketcher::SketchObject",
        "name": name,
        "label": sketch.id,
        "frame": frame.model_dump(include={"origin", "x_dir", "z_dir"}),
        "geometry": [g.model_dump(include={"kind", "values"}) for g in found.geometry],
        "constraints": [_constraint(c, index) for c in constraints],
        "expressions": expressions | placement,
    }


def _endpoint_tangents(constraints: list[Constraint]) -> list[Constraint]:
    # FreeCAD's edge-to-edge tangency is degenerate next to a coincidence at the same point (its gradient vanishes
    # there), so the pair becomes one endpoint tangency: the same three equations
    tangents = [c for c in constraints if c.kind == "tangent"]
    merged: list[Constraint] = []
    for c in constraints:
        t = next((t for t in tangents if c.kind == "coincident" and t.refs[2] in c.refs), None)
        if t is not None:
            tangents.remove(t)
            merged.append(Constraint(kind="tangent", refs=sorted(c.refs, key=lambda r: r.partition(".")[0] != t.refs[0])))
        elif c.kind != "tangent":
            merged.append(c)
    return merged + tangents


def _constraint(c: Constraint, index: dict[str, int]) -> Json:
    def point(ref: str) -> list[int]:
        geo, _, end = ref.partition(".")
        return [index[geo], POSITION.get(end, 1)]

    r = c.refs
    value = math.radians(c.value or 0.0) if c.kind == "angle" else c.value
    match c.kind:
        case "coincident" | "tangent" | "distance" | "distance_x" | "distance_y" if len(r) == 2:
            args = point(r[0]) + point(r[1])
        case "distance_x" | "distance_y":
            # the sketch origin (-1, 1) as first point makes the distance an absolute coordinate
            args = [-1, 1, *point(r[0])]
        case "point_on_object":
            args = [*point(r[0]), index[r[1]]]
        case _:
            args = [index[ref] for ref in r[:2]]
    return {"type": SKETCHER[c.kind], "args": args if value is None else [*args, value]}


def _extrude(f: Extrude, frame: SketchFrame, values: Values) -> Json:
    if f.mode == "intersect" or f.extent == "up_to_next" or evaluate(f.taper, values) != 0:
        raise UnsupportedExportError(f"extrude {f.id!r}: intersect, up-to-next and tapered extrudes have no FreeCAD export yet")
    if f.mode == "add" and f.extent == "through_all":
        raise UnsupportedExportError(f"extrude {f.id!r}: a through-all pad has no FreeCAD equivalent")
    if frame.normal == 0:
        raise UnsupportedExportError(f"extrude {f.id!r}: its profile mixes clockwise and counter-clockwise outlines")
    sign = _sign(f, frame) * frame.normal
    add = f.mode == "add"
    # a Pad grows along the sketch normal, a Pocket against it
    props: Json = {"Reversed": sign < 0 if add else sign > 0, "Type": "Length", "SideType": "One side"}
    lengths = {"Length": f.distance, "Length2": f.distance2 if f.extent == "two_sided" else None}
    if f.extent == "symmetric":
        props["SideType"] = "Symmetric"
    elif f.extent == "two_sided":
        props |= {"SideType": "Two sides", "Type2": "Length"}
    elif f.extent == "through_all":
        props |= {"Type": "ThroughAll", "SideType": "Symmetric" if frame.out == 0 else "One side"}
        lengths = {}
    return _feature("PartDesign::Pad" if add else "PartDesign::Pocket", f.id, f.name, props, lengths, values)


def _hole(f: Hole, frame: SketchFrame, values: Values) -> Json:
    if f.depth is None:
        return _feature("PartDesign::Pocket", f.id, f.name, {"Type": "ThroughAll", "SideType": "Symmetric"}, {}, {})
    # the IR drills against the face normal, which is the sketch normal unless the face looks down the base axis
    props = {"Type": "Length", "SideType": "One side", "Reversed": frame.out < 0}
    return _feature("PartDesign::Pocket", f.id, f.name, props, {"Length": f.depth}, values)


def _hole_sketch(f: Hole, values: Values) -> Sketch:
    if f.type in ("counterbore", "countersink") or (f.drill_point == "118" and f.depth is not None):
        raise UnsupportedExportError(f"hole {f.id!r}: counterbores, countersinks and drill points have no FreeCAD export yet")
    diameter = f.diameter if f.diameter is not None else hole_size(f, values).diameter
    circles = [Circle(kind="circle", center=c, diameter=diameter) for c in _centres(f, values)]
    return Sketch(id=f"{f.id}_centres", plane=f.plane, entities=circles)


def _centres(f: Hole, values: Values) -> list[Point]:
    at = f.at
    if isinstance(at, PointList):
        return at.points
    if isinstance(at, GridPattern):
        nx, ny = round(evaluate(at.count_x, values)), round(evaluate(at.count_y, values))
        xs = [f"({at.center[0]}) + {i - (nx - 1) / 2!r} * ({at.spacing_x})" for i in range(nx)]
        ys = [f"({at.center[1]}) + {j - (ny - 1) / 2!r} * ({at.spacing_y})" for j in range(ny)]
        return [(x, y) for x in xs for y in ys]
    n = round(evaluate(at.count, values))
    angles = [f"({at.start_angle}) + {360 * k / n!r}" for k in range(n)]
    return [(f"({at.center[0]}) + ({at.diameter}) / 2 * cos({a})", f"({at.center[1]}) + ({at.diameter}) / 2 * sin({a})") for a in angles]


def _feature(kind: str, name: str, label: str, props: Json, lengths: dict[str, Expr | None], values: Values) -> Json:
    given = {k: v for k, v in lengths.items() if v is not None}
    expressions = {k: e for k, v in given.items() if (e := _expr(str(v), "distance"))}
    props = props | {k: evaluate(v, values) for k, v in given.items()}
    return {"type": kind, "name": name, "label": label, "profile": f"{name}_sketch", "props": props, "expressions": expressions}


def _sign(f: Extrude, frame: SketchFrame) -> int:
    return -frame.out if f.mode == "cut" and frame.out else frame.out or 1


def _placement(plane: PlaneRef, frame: SketchFrame, extrudes: Extrudes, values: Values) -> dict[str, str]:
    axis = max(range(3), key=lambda i: abs(frame.z_dir[i]))
    key = f"Placement.Base.{'xyz'[axis]}"
    offset = _expr(str(plane.offset), "distance")
    if frame.ref in BASE_PLANES:
        return {} if offset is None else {key: offset if frame.z_dir[axis] > 0 else f"-({offset})"}
    face = _face(frame, axis, extrudes, values)
    if face is None:
        return {}
    position, value, normal = face
    # the sketch sits on the face, moved along the face normal by the plane offset
    if abs(value + normal * evaluate(plane.offset, values) - frame.origin[axis]) > 1e-9:
        return {}
    return {key: f"{position} + {normal} * ({offset or repr(evaluate(plane.offset, values))})"}


def _face(frame: SketchFrame, axis: int, extrudes: Extrudes, values: Values) -> tuple[str, float, int] | None:
    owner_id, _, name = frame.ref.partition(".")
    if owner_id not in extrudes:
        return None
    f, owner = extrudes[owner_id]
    if f.extent != "blind" or abs(owner.z_dir[axis]) < 0.999:
        return None
    # "end" faces the extrude's nominal direction; the prism itself grows along the profile's face normal
    nominal = round(owner.z_dir[axis]) * _sign(f, owner)
    grows = nominal * owner.normal
    named = AXIS_FACES.get(ALIASES.get(name, name))
    normal = {"end": nominal, "start": -nominal}.get(name) or (named[1] if named and named[0] == axis else None)
    if normal is None:
        return None
    start = f"{owner_id}_sketch.Placement.Base.{'xyz'[axis]} / 1 mm"
    if normal != grows:
        return start, owner.origin[axis], normal
    return f"{start} + {grows} * {owner_id}.Length / 1 mm", owner.origin[axis] + grows * evaluate(f.distance or 0.0, values), normal


def _expr(e: str | None, kind: str) -> str | None:
    if e is None or not names(e):
        return None
    found = _freecad(parse(e))
    return f"{found} * 1 deg" if found and kind == "angle" else found


def _freecad(node: ast.expr) -> str | None:
    match node:
        case ast.Constant(value=int() | float() as v):
            return repr(float(v))
        case ast.Name(id=name):
            return f"{SHEET}.{alias(name)}"
        case ast.UnaryOp(op=ast.USub(), operand=x):
            inner = _freecad(x)
            return None if inner is None else f"-({inner})"
        case ast.Call(func=ast.Name(id=name), args=[x]) if name in FUNCTIONS:
            inner = _freecad(x)
            return None if inner is None else f"{name}({inner})"
        case ast.BinOp(left=a, op=op, right=b) if type(op) in OPERATORS:
            left, right = _freecad(a), _freecad(b)
            return None if left is None or right is None else f"({left} {OPERATORS[type(op)]} {right})"
    return None
