from scriber_ir.assembly import effective_assembly
from scriber_ir.compile_assembly import MATE_PRELUDE, assembly_build
from scriber_ir.compile_features import high_level
from scriber_ir.expr import to_python
from scriber_ir.fasteners import hole_size, thread_size
from scriber_ir.model import (
    HIGH_LEVEL,
    AirfoilSection,
    Bend,
    BossPattern,
    Chamfer,
    Circle,
    Datum,
    Design,
    Draft,
    Ellipse,
    Expr,
    Extrude,
    Feature,
    Fillet,
    Flange,
    GridPattern,
    Groove,
    Hole,
    Keyway,
    Lid,
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
    Rib,
    Selector,
    SheetMetal,
    Shell,
    ShellWithLid,
    Sketch,
    Slot,
    Spline,
    SpurGear,
    Thread,
    Tube,
)
from scriber_ir.prelude import AIRFOIL_PRELUDE, PRELUDE
from scriber_ir.prelude_features import FEATURE_PRELUDE


# trace=True adds a _trace(part, feature, shape) call after every feature, for the caller to define.
def compile_design(design: Design, trace: bool = False) -> str:
    params = "\n".join(f"    {p.name!r}: {p.value!r},  # {p.unit or 'count'} {p.description}".rstrip() for p in design.params)
    values = design.param_values()
    enclosures = {p.id: f for p in design.parts for f in p.features if isinstance(f, ShellWithLid)}
    parts = "\n\n\n".join(_part(i, p, values, enclosures, trace) for i, p in enumerate(design.parts))
    table = ", ".join(f"{p.id!r}: part_{i}()" for i, p in enumerate(design.parts))
    airfoils = any(isinstance(f, AirfoilSection) for p in design.parts for f in p.features)
    prelude = PRELUDE + AIRFOIL_PRELUDE if airfoils else PRELUDE
    if any(isinstance(f, (*HIGH_LEVEL, Thread)) or (isinstance(f, Hole) and f.type == "tapped") for p in design.parts for f in p.features):
        prelude += FEATURE_PRELUDE
    faces = "\nFACES = {}\n" if any(p.face_groups for p in design.parts) else ""
    build = f"def build():\n    return {{{table}}}\n"
    if effective_assembly(design) is not None:
        prelude, build = prelude + MATE_PRELUDE, assembly_build(design)
    return f"{prelude}\n\nP = {{\n{params}\n}}\n{faces}\n\n{parts}\n\n\n{build}"


def _part(index: int, part: Part, values: dict[str, float], enclosures: dict[str, ShellWithLid], trace: bool) -> str:
    sketches = {s.id: s for s in part.sketches}
    datums = ", ".join(_datum(d) for d in part.datums)
    body = []
    for f in part.features:
        comment, *lines = _feature(f, sketches, values, enclosures)
        # every feature runs even when an earlier one failed, so one build reports all the failures at once
        body += [comment, f"    _at({part.id!r}, {f.id!r})", "    try:", *(f"    {line}" for line in lines)]
        body += ["    except Exception as e:", f"        _failed({f.id!r}, e)"]
        if trace:
            body.append(f"    _trace({part.id!r}, {f.id!r}, part)")
    head = [f"def part_{index}():", "    part = None", "    T = {}", f"    D = {{{datums}}}"]
    groups = ", ".join(f"{g.name!r}: {_select('faces', g.faces)}" for g in part.face_groups)
    faces = [f"    FACES[{part.id!r}] = {{{groups}}}"] if groups else []
    return "\n".join([*head, *body, "    _raise_failed()", *faces, f"    part.label = {part.name!r}", "    return part"])


def _datum(d: Datum) -> str:
    if d.origin is not None and d.normal is not None:
        return f"{d.id!r}: _plane({_pt(d.origin)}, {_pt(d.normal)}, {_pt(d.x_dir) if d.x_dir else None})"
    return f"{d.id!r}: _datum({d.base!r}, {_x(d.offset)}, {d.rotate_about!r}, {_x(d.angle)})"


def _feature(f: Feature, sketches: dict[str, Sketch], values: dict[str, float], enclosures: dict[str, ShellWithLid]) -> list[str]:
    head = f"    # {f.id} {f.name}" + (f": {f.intent}" if f.intent else "")
    return [head, *_body(f, sketches, values, enclosures)]


def _body(f: Feature, sketches: dict[str, Sketch], values: dict[str, float], enclosures: dict[str, ShellWithLid]) -> list[str]:
    match f:
        case Extrude() if f.wrap is not None:
            sk = sketches[f.sketch]
            return [
                *_on(sk.plane),
                f"    tool = _wrap(part, T[{f.wrap!r}][0], pl, {_shape(sk)}, {f.mode!r}, {_opt(f.distance)})",
                f"    part = _apply(part, tool, {f.mode!r}, 'wrapped {f.id}')",
                f"    T[{f.id!r}] = (tool, {f.mode!r}, None)",
            ]
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
            cs = _or(f.cs_diameter, size.cs_diameter) if f.type == "countersink" or f.cs_diameter is not None else "None"
            dims = f"{diameter}, {_opt(f.depth)}, {cb[0]}, {cb[1]}, {cs}, {_x(f.cs_angle)}"
            return [
                *_on(f.plane),
                f"    tool = _hole(part, pl, out, {_placement(f.at)}, {dims}, {f.drill_point == '118'}, {f.through == 'next'})",
                f"    part = _apply(part, tool, 'cut', 'hole {f.id}')",
                f"    T[{f.id!r}] = (tool, 'cut', None)",
                *_tapped(f, values),
            ]
        case Pattern():
            spacing = "None" if f.spacing is None else _x(f.spacing)
            center = f"({', '.join(_x(c) for c in f.center)})"
            args = f"{f.features!r}, {f.type!r}, {_x(f.count)}, {f.direction!r}, {spacing}, {f.axis!r}, {center}, {_x(f.angle)}"
            return [f"    part = _pattern(part, T, {args}, {f.mirror_plane!r})"]
        case Fillet():
            return [f"    part = _fillet(part, {f.id!r}, lambda: {_select('edges', f.edges)}, {_x(f.radius)})"]
        case Chamfer():
            return [f"    part = _chamfer(part, {f.id!r}, lambda: {_select('edges', f.edges)}, {_x(f.length)}, {_opt(f.length2)})"]
        case Draft():
            return [*_on(f.neutral), f"    part = _draft(part, {f.id!r}, lambda: {_select('faces', f.faces)}, pl, {_x(f.angle)})"]
        case Shell():
            faces = " + ".join(_select("faces", s) for s in f.open) or "[]"
            return [f"    part = _shell(part, {faces}, {_x(f.thickness)})"]
        case Tube():
            points = ", ".join(_pt(p) for p in f.points)
            wall = "None" if f.wall is None else _x(f.wall)
            return [
                f"    tool = _tube([{points}], {_x(f.outer_diameter)}, {wall}, {_x(f.bend_radius)})",
                f"    part = _apply(part, tool, {f.mode!r}, 'tube {f.id}')",
                f"    T[{f.id!r}] = (tool, {f.mode!r}, None)",
            ]
        case Thread():
            major, pitch = thread_size(f.designation)
            args = f"{f.on!r}, {_x(f.position)}, {_opt(f.length)}, {major!r}, {pitch!r}, {f.modelled}, 'thread {f.id}'"
            return [
                f"    tool = _thread(part, T[{f.of!r}][0], {args})",
                f"    part = part if tool is None else _apply(part, tool, 'cut', 'thread {f.id}')",
            ]
        case SheetMetal():
            sk = sketches[f.sketch]
            bends = ", ".join(f"({_pt(b.line[0])}, {_pt(b.line[1])}, {_fold(b, f.bend_radius)}, {_opt(b.relief)})" for b in f.bends)
            flanges = ", ".join(f"({_pt(g.edge[0])}, {_pt(g.edge[1])}, {_x(g.length)}, {_fold(g, f.bend_radius)})" for g in f.flanges)
            return [
                *_on(sk.plane),
                f"    tool = _sheet(pl, {_shape(sk)}, {_x(f.thickness)}, {_x(f.k_factor)}, [{bends}], [{flanges}])",
                "    part = _apply(part, tool, 'add')",
                f"    T[{f.id!r}] = (tool, 'add', None)",
            ]
        case AirfoilSection():
            return [*_on(f.plane), f"    T[{f.id!r}] = pl * _airfoil({f.naca!r}, {_x(f.chord)}, {_pt(f.leading_edge)}, {_x(f.twist)})"]
        case Loft():
            # sketch sections are placed here; their keys cannot clash with feature ids
            placed = [line for s in f.sections if s in sketches for line in _section(s, sketches[s])]
            sections = ", ".join(f"T['sketch:{s}']" if s in sketches else f"T[{s!r}]" for s in f.sections)
            body = f"loft([{sections}], ruled={f.ruled})" if f.wall is None else f"_hollow([{sections}], {_x(f.wall)}, {f.ruled})"
            return [
                *placed,
                f"    tool = {body}",
                f"    part = _apply(part, tool, {f.mode!r}, 'loft {f.id}')",
                f"    T[{f.id!r}] = (tool, {f.mode!r}, None)",
            ]
        case SpurGear() | Rib() | BossPattern() | ShellWithLid() | Lid() | Keyway() | Groove():
            on = _on(f.plane) if isinstance(f, SpurGear | Rib | BossPattern) else []
            return high_level(f, on, _placement(f.at) if isinstance(f, BossPattern) else "", enclosures)


def _tapped(f: Hole, values: dict[str, float]) -> list[str]:
    if f.type != "tapped" or f.fastener is None:
        return []
    major, pitch = thread_size(f.thread or f.fastener)
    length = _opt(f.thread_depth if f.thread_depth is not None else f.depth)
    return [f"    _tapped(pl, out, {_placement(f.at)}, {major!r}, {pitch!r}, {length}, 'hole {f.id}')"]


def _fold(b: Bend | Flange, default_radius: Expr) -> str:
    return f"{_x(b.angle)}, {b.direction == 'up'}, {_x(b.radius or default_radius)}"


def _on(plane: PlaneRef) -> list[str]:
    return [f"    pl, out = _ref(part, T, D, {plane.ref!r}, {_x(plane.offset)})"]


def _section(sid: str, sk: Sketch) -> list[str]:
    return [*_on(sk.plane), f"    T['sketch:{sid}'] = pl * ({_shape(sk)})"]


def _select(kind: str, s: Selector) -> str:
    args = f"{s.of!r}, {s.meets!r}, {_dir(s.normal)}, {_dir(s.parallel)}, {s.convexity!r}, {s.extreme!r}"
    args += f", {s.geom!r}, {_opt(s.arc_radius)}, {s.outline}"
    return f"_select(part, T, {kind!r}, {args})"


def _dir(d: str | tuple[Expr, Expr, Expr]) -> str:
    return repr(d) if isinstance(d, str) else _pt(d)


def _shape(s: Sketch) -> str:
    add = [_entity(e) for e in s.entities if not e.subtract]
    sub = [_entity(e) for e in s.entities if e.subtract]
    return " + ".join(add) + "".join(f" - {e}" for e in sub)


def _entity(e: Rect | Circle | Polygon | Slot | Path | Ellipse | Spline) -> str:
    match e:
        case Ellipse():
            return f"{_pos(e.center)} * Rot(0, 0, {_x(e.angle)}) * Ellipse({_x(e.width)} / 2, {_x(e.height)} / 2)"
        case Spline():
            return f"_spline([{', '.join(_pt(p) for p in e.points)}])"
        case Rect():
            turn = "" if e.angle == 0 else f" * Rot(0, 0, {_x(e.angle)})"
            return f"{_pos(e.center)}{turn} * _rect({_x(e.width)}, {_x(e.height)}, {_x(e.corner_radius)})"
        case Circle():
            return f"{_pos(e.center)} * Circle({_x(e.diameter)} / 2)"
        case Polygon():
            return f"Polygon({', '.join(_pt(p) for p in e.points)}, align=None)"
        case Slot():
            return f"{_pos(e.center)} * SlotOverall({_x(e.length)}, {_x(e.width)}, rotation={_x(e.angle)})"
        case Path():
            segments = ", ".join(
                f"({_pt(s.to)}, {s.arc!r}, {_opt(s.radius)}, {_x(s.fillet)}{'' if s.center is None else ', ' + _pt(s.center)})"
                for s in e.segments
            )
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


def _pt(p: tuple[Expr, ...]) -> str:
    return f"({', '.join(_x(v) for v in p)})"


def _opt(e: Expr | None) -> str:
    return "None" if e is None else _x(e)


def _or(e: Expr | None, table: float | None) -> str:
    return _x(e) if e is not None else repr(table)


def _x(e: Expr) -> str:
    return to_python(e)
