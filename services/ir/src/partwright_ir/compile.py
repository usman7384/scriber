from partwright_ir.expr import to_python
from partwright_ir.model import (
    Chamfer,
    Circle,
    Design,
    Expr,
    Extrude,
    Feature,
    Fillet,
    GridPattern,
    Hole,
    Part,
    Placement,
    PointList,
    PolarPattern,
    Polygon,
    Rect,
    Revolve,
    Shell,
    Sketch,
    SketchPlane,
    Slot,
)

PRELUDE = """import math

from build123d import *


def sin(d): return math.sin(math.radians(d))
def cos(d): return math.cos(math.radians(d))
def tan(d): return math.tan(math.radians(d))
def sqrt(x): return math.sqrt(x)


def _plane(base, offset):
    return {"XY": Plane.XY, "XZ": Plane.XZ, "YZ": Plane.YZ}[base].offset(offset)


def _rect(w, h, r):
    return RectangleRounded(w, h, r) if r > 0 else Rectangle(w, h)


def _grid(cx, cy, nx, ny, sx, sy):
    nx, ny = round(nx), round(ny)
    return [(cx + (i - (nx - 1) / 2) * sx, cy + (j - (ny - 1) / 2) * sy) for i in range(nx) for j in range(ny)]


def _polar(cx, cy, n, d, a0):
    n = round(n)
    return [(cx + d / 2 * cos(a0 + 360 * k / n), cy + d / 2 * sin(a0 + 360 * k / n)) for k in range(n)]


def _hole(part, plane, points, d, depth, cbd, cbdepth):
    through = depth is None
    length = 4 * part.bounding_box().diagonal if through else depth
    align = (Align.CENTER, Align.CENTER, Align.CENTER if through else Align.MAX)
    before = part.volume
    box = part.bounding_box()
    for x, y in points:
        _inside_outline(box, plane.from_local_coords((x, y)), plane.z_dir, d / 2, (x, y))
        at = plane * Pos(x, y)
        part -= at * Cylinder(d / 2, length, align=align)
        if cbd is not None:
            part -= at * Cylinder(cbd / 2, cbdepth, align=(Align.CENTER, Align.CENTER, Align.MAX))
    if part.volume >= before - 1e-9:
        raise ValueError("hole removed no material: the centres or the plane offset miss the part, or a blind hole points away from it")
    return part


def _inside_outline(box, c, n, r, at):
    drill = "XYZ"[max(range(3), key=lambda i: abs((n.X, n.Y, n.Z)[i]))]
    for name, lo, hi, ci, ni in zip("XYZ", box.min, box.max, (c.X, c.Y, c.Z), (n.X, n.Y, n.Z)):
        if abs(ni) >= 0.5 or lo + r - 1e-6 <= ci <= hi - r + 1e-6:
            continue
        if hi - lo < 2 * r:
            where = f"the part is only {hi - lo:g} mm along {name}, less than the hole diameter"
            where += f"; this hole drills along {drill}, so its plane is probably wrong"
        else:
            where = f"its centre {name} must be between {lo + r:g} and {hi - r:g} (the hole drills along {drill})"
        raise ValueError(f"hole at ({at[0]:g}, {at[1]:g}) lies outside the part: {where}")


def _cut(part, tool):
    before = part.volume
    part -= tool
    if part.volume >= before - 1e-9:
        raise ValueError("cut removed no material: the sketch misses the part or the extrude points away from it")
    return part


def _edges(part, which):
    if which == "all":
        return part.edges()
    if which in ("top", "bottom"):
        faces = part.faces().sort_by(Axis.Z)
        return (faces[-1] if which == "top" else faces[0]).edges()
    curved = {e for f in part.faces() if f.geom_type != GeomType.PLANE for e in f.edges()}
    axis = {"parallel_x": Axis.X, "parallel_y": Axis.Y, "parallel_z": Axis.Z}[which]
    return [e for e in part.edges().filter_by(axis) if e not in curved]


def _shell(part, open_face, t):
    if open_face == "none":
        return part - offset(part, amount=-t)
    faces = part.faces().sort_by(Axis.Z)
    return offset(part, amount=-t, openings=faces[-1] if open_face == "top" else faces[0])
"""


def compile_design(design: Design) -> str:
    params = "\n".join(f"    {p.name!r}: {p.value!r},  # {p.unit or 'count'} {p.description}".rstrip() for p in design.params)
    parts = "\n\n\n".join(_part(i, p) for i, p in enumerate(design.parts))
    table = ", ".join(f"{p.id!r}: part_{i}()" for i, p in enumerate(design.parts))
    return f"{PRELUDE}\n\nP = {{\n{params}\n}}\n\n\n{parts}\n\n\ndef build():\n    return {{{table}}}\n"


def _part(index: int, part: Part) -> str:
    sketches = {s.id: s for s in part.sketches}
    body = [line for f in part.features for line in _feature(f, sketches)]
    label = f"    part.label = {part.name!r}"
    return f"def part_{index}():\n    part = None\n" + "\n".join(body) + f"\n{label}\n    return part"


def _sketch(s: Sketch) -> str:
    add = [_entity(e) for e in s.entities if not e.subtract]
    sub = [_entity(e) for e in s.entities if e.subtract]
    shape = " + ".join(add) + "".join(f" - {e}" for e in sub)
    return f"{_plane(s.plane)} * ({shape})"


def _entity(e: Rect | Circle | Polygon | Slot) -> str:
    match e:
        case Rect():
            return f"{_pos(e.center)} * _rect({_x(e.width)}, {_x(e.height)}, {_x(e.corner_radius)})"
        case Circle():
            return f"{_pos(e.center)} * Circle({_x(e.diameter)} / 2)"
        case Polygon():
            return f"Polygon({', '.join(_pt(p) for p in e.points)}, align=None)"
        case Slot():
            return f"{_pos(e.center)} * SlotOverall({_x(e.length)}, {_x(e.width)}, rotation={_x(e.angle)})"


def _feature(f: Feature, sketches: dict[str, Sketch]) -> list[str]:
    head = f"    # {f.id} {f.name}" + (f": {f.intent}" if f.intent else "")
    return [head, *_feature_body(f, sketches)]


def _feature_body(f: Feature, sketches: dict[str, Sketch]) -> list[str]:
    match f:
        case Extrude():
            amount = f"{_x(f.distance)} / 2, both=True" if f.symmetric else _x(f.distance)
            return _combine(f"extrude({_sketch(sketches[f.sketch])}, amount={amount})", f.mode)
        case Revolve():
            sk = sketches[f.sketch]
            axis = "x_dir" if f.axis == "X" else "y_dir"
            return [
                f"    sk = {_sketch(sk)}",
                f"    pl = {_plane(sk.plane)}",
                *_combine(f"revolve(sk, axis=Axis(pl.origin, pl.{axis}), revolution_arc={_x(f.angle)})", f.mode),
            ]
        case Hole():
            depth = "None" if f.depth is None else _x(f.depth)
            cbd = "None" if f.counterbore_diameter is None else _x(f.counterbore_diameter)
            cbdepth = "None" if f.counterbore_depth is None else _x(f.counterbore_depth)
            args = f"part, {_plane(f.plane)}, {_placement(f.at)}, {_x(f.diameter)}, {depth}, {cbd}, {cbdepth}"
            return [f"    part = _hole({args})"]
        case Fillet():
            return [f"    part = fillet(_edges(part, {f.edges!r}), radius={_x(f.radius)})"]
        case Chamfer():
            return [f"    part = chamfer(_edges(part, {f.edges!r}), length={_x(f.length)})"]
        case Shell():
            return [f"    part = _shell(part, {f.open_face!r}, {_x(f.thickness)})"]


def _combine(solid: str, mode: str) -> list[str]:
    if mode == "cut":
        return [f"    part = _cut(part, {solid})"]
    return [f"    s = {solid}", "    part = s if part is None else part + s"]


def _plane(p: SketchPlane) -> str:
    return f"_plane({p.base!r}, {_x(p.offset)})"


def _placement(at: Placement) -> str:
    match at:
        case GridPattern():
            c = at.center
            return f"_grid({_x(c[0])}, {_x(c[1])}, {_x(at.count_x)}, {_x(at.count_y)}, {_x(at.spacing_x)}, {_x(at.spacing_y)})"
        case PolarPattern():
            c = at.center
            return f"_polar({_x(c[0])}, {_x(c[1])}, {_x(at.count)}, {_x(at.diameter)}, {_x(at.start_angle)})"
        case PointList():
            return f"[{', '.join(_pt(p) for p in at.points)}]"


def _pos(p: tuple[Expr, Expr]) -> str:
    return f"Pos({_x(p[0])}, {_x(p[1])})"


def _pt(p: tuple[Expr, Expr]) -> str:
    return f"({_x(p[0])}, {_x(p[1])})"


def _x(e: Expr) -> str:
    return to_python(e)
