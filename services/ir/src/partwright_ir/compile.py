from partwright_ir.compile_assembly import MATE_PRELUDE, assembly_build
from partwright_ir.expr import to_python
from partwright_ir.fasteners import hole_size
from partwright_ir.model import (
    AirfoilSection,
    Chamfer,
    Circle,
    Datum,
    Design,
    Expr,
    Extrude,
    Feature,
    Fillet,
    GridPattern,
    Hole,
    Loft,
    Part,
    Path,
    Pattern,
    Placement,
    PlaneRef,
    PointList,
    PolarPattern,
    Polygon,
    Rect,
    Revolve,
    Selector,
    Shell,
    Sketch,
    Slot,
)
from partwright_ir.prelude import AIRFOIL_PRELUDE, PRELUDE


def compile_design(design: Design) -> str:
    params = "\n".join(f"    {p.name!r}: {p.value!r},  # {p.unit or 'count'} {p.description}".rstrip() for p in design.params)
    values = design.param_values()
    parts = "\n\n\n".join(_part(i, p, values) for i, p in enumerate(design.parts))
    table = ", ".join(f"{p.id!r}: part_{i}()" for i, p in enumerate(design.parts))
    airfoils = any(isinstance(f, AirfoilSection) for p in design.parts for f in p.features)
    prelude = PRELUDE + AIRFOIL_PRELUDE if airfoils else PRELUDE
    build = f"def build():\n    return {{{table}}}\n"
    if design.assembly is not None:
        prelude, build = prelude + MATE_PRELUDE, assembly_build(design)
    return f"{prelude}\n\nP = {{\n{params}\n}}\n\n\n{parts}\n\n\n{build}"


def _part(index: int, part: Part, values: dict[str, float]) -> str:
    sketches = {s.id: s for s in part.sketches}
    datums = ", ".join(_datum(d) for d in part.datums)
    body = [line for f in part.features for line in _feature(f, sketches, values)]
    head = [f"def part_{index}():", "    part = None", "    T = {}", f"    D = {{{datums}}}"]
    return "\n".join([*head, *body, f"    part.label = {part.name!r}", "    return part"])


def _datum(d: Datum) -> str:
    return f"{d.id!r}: _datum({d.base!r}, {_x(d.offset)}, {d.rotate_about!r}, {_x(d.angle)})"


def _feature(f: Feature, sketches: dict[str, Sketch], values: dict[str, float]) -> list[str]:
    head = f"    # {f.id} {f.name}" + (f": {f.intent}" if f.intent else "")
    return [head, *_body(f, sketches, values)]


def _body(f: Feature, sketches: dict[str, Sketch], values: dict[str, float]) -> list[str]:
    match f:
        case Extrude():
            sk = sketches[f.sketch]
            args = f"{f.mode!r}, {f.extent!r}, {_opt(f.distance)}, {_opt(f.distance2)}, {_x(f.taper)}"
            return [
                *_on(sk.plane),
                f"    sk = pl * ({_shape(sk)})",
                f"    tool, direction = _extrude(part, sk, pl, out, {args})",
                f"    part = _apply(part, tool, {f.mode!r})",
                f"    T[{f.id!r}] = (tool, {f.mode!r}, direction)",
            ]
        case Revolve():
            sk = sketches[f.sketch]
            return [
                *_on(sk.plane),
                f"    sk = pl * ({_shape(sk)})",
                f"    tool = _revolve(sk, pl, {f.axis!r}, {_x(f.axis_offset)}, {_x(f.angle)})",
                f"    part = _apply(part, tool, {f.mode!r})",
                f"    T[{f.id!r}] = (tool, {f.mode!r}, None)",
            ]
        case Hole():
            size = hole_size(f, values)
            diameter = repr(size.diameter) if f.diameter is None else _x(f.diameter)
            cb = (_or(f.cb_diameter, size.cb_diameter), _or(f.cb_depth, size.cb_depth)) if f.type == "counterbore" else ("None", "None")
            cs = _or(f.cs_diameter, size.cs_diameter) if f.type == "countersink" else "None"
            dims = f"{diameter}, {_opt(f.depth)}, {cb[0]}, {cb[1]}, {cs}, {_x(f.cs_angle)}"
            return [
                *_on(f.plane),
                f"    tool = _hole(part, pl, out, {_placement(f.at)}, {dims}, {f.drill_point == '118'})",
                f"    part = _apply(part, tool, 'cut', 'hole {f.id}')",
                f"    T[{f.id!r}] = (tool, 'cut', None)",
            ]
        case Pattern():
            spacing = "None" if f.spacing is None else _x(f.spacing)
            center = f"({', '.join(_x(c) for c in f.center)})"
            args = f"{f.features!r}, {f.type!r}, {_x(f.count)}, {f.direction!r}, {spacing}, {f.axis!r}, {center}, {_x(f.angle)}"
            return [f"    part = _pattern(part, T, {args}, {f.mirror_plane!r})"]
        case Fillet():
            return [f"    part = fillet({_select('edges', f.edges)}, radius={_x(f.radius)})"]
        case Chamfer():
            length2 = "" if f.length2 is None else f", length2={_x(f.length2)}"
            return [f"    part = chamfer({_select('edges', f.edges)}, length={_x(f.length)}{length2})"]
        case Shell():
            faces = " + ".join(_select("faces", s) for s in f.open) or "[]"
            return [f"    part = _shell(part, {faces}, {_x(f.thickness)})"]
        case AirfoilSection():
            return [*_on(f.plane), f"    T[{f.id!r}] = pl * _airfoil({f.naca!r}, {_x(f.chord)}, {_pt(f.leading_edge)}, {_x(f.twist)})"]
        case Loft():
            return [
                f"    tool = loft([{', '.join(f'T[{s!r}]' for s in f.sections)}], ruled={f.ruled})",
                "    part = _apply(part, tool, 'add')",
                f"    T[{f.id!r}] = (tool, 'add', None)",
            ]


def _on(plane: PlaneRef) -> list[str]:
    return [f"    pl, out = _ref(part, T, D, {plane.ref!r}, {_x(plane.offset)})"]


def _select(kind: str, s: Selector) -> str:
    return f"_select(part, T, {kind!r}, {s.of!r}, {s.normal!r}, {s.parallel!r}, {s.convexity!r}, {s.extreme!r})"


def _shape(s: Sketch) -> str:
    add = [_entity(e) for e in s.entities if not e.subtract]
    sub = [_entity(e) for e in s.entities if e.subtract]
    return " + ".join(add) + "".join(f" - {e}" for e in sub)


def _entity(e: Rect | Circle | Polygon | Slot | Path) -> str:
    match e:
        case Rect():
            return f"{_pos(e.center)} * _rect({_x(e.width)}, {_x(e.height)}, {_x(e.corner_radius)})"
        case Circle():
            return f"{_pos(e.center)} * Circle({_x(e.diameter)} / 2)"
        case Polygon():
            return f"Polygon({', '.join(_pt(p) for p in e.points)}, align=None)"
        case Slot():
            return f"{_pos(e.center)} * SlotOverall({_x(e.length)}, {_x(e.width)}, rotation={_x(e.angle)})"
        case Path():
            segments = ", ".join(f"({_pt(s.to)}, {s.arc!r}, {_opt(s.radius)}, {_x(s.fillet)})" for s in e.segments)
            return f"_path({_pt(e.start)}, [{segments}])"


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


def _opt(e: Expr | None) -> str:
    return "None" if e is None else _x(e)


def _or(e: Expr | None, table: float | None) -> str:
    return _x(e) if e is not None else repr(table)


def _x(e: Expr) -> str:
    return to_python(e)
