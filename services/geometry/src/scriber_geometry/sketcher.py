import math
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

from scriber_geometry.models import Constraint, ConstraintKind, GeoKind, SketchDof, SketchGeo
from scriber_ir import Design, evaluate
from scriber_ir.model import Circle, Entity, Expr, Path, Polygon, Rect, Sketch, Slot

Array = npt.NDArray[np.float64]
Vec2 = tuple[float, float]
SIZES = {"point": 2, "line": 4, "arc": 5, "circle": 3}
RANK_TOL = 1e-6


class UnsupportedSketchError(ValueError):
    pass


@dataclass(frozen=True)
class Geo:
    name: str
    kind: GeoKind
    at: int


@dataclass(frozen=True)
class Seg:
    start: str
    end: str
    geo: Geo


@dataclass
class Builder:
    values: dict[str, float]
    geos: dict[str, Geo] = field(default_factory=dict)
    x0: list[float] = field(default_factory=list)
    wanted: list[Constraint] = field(default_factory=list)

    def add(self, kind: GeoKind, *values: float) -> Geo:
        geo = Geo(f"g{len(self.geos)}", kind, len(self.x0))
        self.geos[geo.name] = geo
        self.x0.extend(values)
        return geo

    def want(self, kind: ConstraintKind, *refs: str, value: float | None = None, expr: str | None = None) -> None:
        self.wanted.append(Constraint(kind=kind, refs=list(refs), value=value, expr=expr))

    def num(self, e: Expr) -> float:
        return evaluate(e, self.values)

    def at(self, ref: str) -> Array:
        return _point(ref, np.array(self.x0), self.geos)


def sketch_dof(design: Design, seed: int = 0) -> list[SketchDof]:
    return [analyse_sketch(part.id, s, design.param_values(), seed) for part in design.parts for s in part.sketches]


def remaining_dof(geometry: list[SketchGeo], constraints: list[Constraint]) -> int:
    geos: dict[str, Geo] = {}
    x0: list[float] = []
    for g in geometry:
        geos[g.name] = Geo(g.name, g.kind, len(x0))
        x0 += g.values
    if not constraints:
        return len(x0)
    rows = np.vstack([_jacobian(_bound(c, geos), np.array(x0)) for c in constraints])
    return len(x0) - int(np.linalg.matrix_rank(rows, tol=RANK_TOL))


def analyse_sketch(part: str, sketch: Sketch, values: dict[str, float], seed: int) -> SketchDof:
    b = Builder(values)
    try:
        for e in sketch.entities:
            _entity(b, e)
    except UnsupportedSketchError as e:
        return SketchDof(part=part, sketch=sketch.id, geometry=[], unknowns=0, constraints=[], redundant=0, dof=None, note=str(e))
    x0 = np.array(b.x0)
    chosen, rows = [], np.zeros((0, len(x0)))
    for c in b.wanted:
        for option in [c, *_axes(c)]:
            stacked = np.vstack([rows, _jacobian(_bound(option, b.geos), x0)])
            if np.linalg.matrix_rank(stacked, tol=RANK_TOL) == len(stacked):
                chosen.append(option)
                rows = stacked
                if option is c:
                    break
    return SketchDof(
        part=part,
        sketch=sketch.id,
        geometry=[SketchGeo(name=g.name, kind=g.kind, values=b.x0[g.at : g.at + SIZES[g.kind]]) for g in b.geos.values()],
        unknowns=len(x0),
        constraints=chosen,
        redundant=len(b.wanted) - len(chosen),
        dof=len(x0) - len(rows),
        solve_error=_solve_error(chosen, b.geos, x0, seed),
    )


def _axes(c: Constraint) -> list[Constraint]:
    # a coincidence that is only half redundant (a closed chain of collinear lines) still pins the other axis
    if c.kind != "coincident":
        return []
    return [c.model_copy(update={"kind": kind, "value": 0.0}) for kind in ("distance_x", "distance_y")]


def _bound(c: Constraint, geos: dict[str, Geo]) -> Callable[[Array], Array]:
    return lambda x: _residual(c, x, geos)


def _solve_error(constraints: list[Constraint], geos: dict[str, Geo], x0: Array, seed: int) -> float:
    # re-solve from a perturbed start: with 0 DOF the solver must land back on the IR geometry
    def f(x: Array) -> Array:
        return np.concatenate([_residual(c, x, geos) for c in constraints])

    x = x0 + np.random.default_rng(seed).normal(0, 0.1, len(x0))
    for _ in range(50):
        r = f(x)
        if np.abs(r).max() < 1e-12:
            break
        x = x + np.linalg.lstsq(_jacobian(f, x), -r, rcond=None)[0]
    return float(np.abs(x - x0).max())


def _jacobian(f: Callable[[Array], Array], x: Array, h: float = 1e-6) -> Array:
    return np.array([(f(x + d) - f(x - d)) / (2 * h) for d in np.eye(len(x)) * h]).T


def _residual(c: Constraint, x: Array, geos: dict[str, Geo]) -> Array:
    def p(ref: str) -> Array:
        return _point(ref, x, geos)

    def g(ref: str) -> Array:
        return x[geos[ref].at : geos[ref].at + SIZES[geos[ref].kind]]

    r, v = c.refs, c.value or 0.0
    match c.kind:
        case "coincident":
            return p(r[0]) - p(r[1])
        case "horizontal" | "vertical":
            return np.array([(g(r[0])[2:4] - g(r[0])[:2])[1 if c.kind == "horizontal" else 0]])
        case "angle":
            d = _unit(g(r[0])[2:4] - g(r[0])[:2])
            return np.array([math.sin(math.radians(v)) * d[0] - math.cos(math.radians(v)) * d[1]])
        case "tangent":
            return np.array([_tangency(g(r[0]), geos[r[0]].kind, g(r[1]), p(r[2]))])
        case "point_on_object":
            return np.array([_off_curve(p(r[0]), g(r[1]), geos[r[1]].kind)])
        case "radius" | "diameter":
            return np.array([g(r[0])[2] * (2 if c.kind == "diameter" else 1) - v])
        case "distance":
            return np.array([np.linalg.norm(p(r[1]) - p(r[0])) - v])
        case "distance_x" | "distance_y":
            i = 0 if c.kind == "distance_x" else 1
            return np.array([(p(r[1])[i] - p(r[0])[i] if len(r) == 2 else p(r[0])[i]) - v])


def _point(ref: str, x: Array, geos: dict[str, Geo]) -> Array:
    name, _, end = ref.partition(".")
    geo = geos[name]
    v = x[geo.at : geo.at + SIZES[geo.kind]]
    if geo.kind == "point" or end == "center":
        return v[:2]
    if geo.kind == "line":
        return v[:2] if end == "start" else v[2:4]
    angle = v[3] if end == "start" else v[4]
    return v[:2] + np.array([math.cos(angle), math.sin(angle)]) * float(v[2])


def _tangency(a: Array, kind_a: str, b: Array, at: Array) -> float:
    if kind_a == "line":
        return float(np.dot(_unit(a[2:4] - a[:2]), _unit(at - b[:2])))
    ra, rb = _unit(at - a[:2]), _unit(at - b[:2])
    return float(ra[0] * rb[1] - ra[1] * rb[0])


def _off_curve(q: Array, geo: Array, kind: str) -> float:
    if kind == "line":
        d, w = _unit(geo[2:4] - geo[:2]), q - geo[:2]
        return float(d[0] * w[1] - d[1] * w[0])
    return float(np.linalg.norm(q - geo[:2]) - geo[2])


def _unit(v: Array) -> Array:
    return v / np.linalg.norm(v)


def _entity(b: Builder, e: Entity) -> None:
    match e:
        case Rect():
            _rect(b, e)
        case Circle():
            geo = b.add("circle", b.num(e.center[0]), b.num(e.center[1]), b.num(e.diameter) / 2)
            b.want("diameter", geo.name, value=b.num(e.diameter), expr=_t(e.diameter))
            _fix(b, f"{geo.name}.center", e.center)
        case Polygon():
            pts = [(b.num(x), b.num(y)) for x, y in e.points]
            segs = [_line(b, p, q) for p, q in zip(pts, pts[1:] + pts[:1], strict=True)]
            _chain(b, segs)
            for s, pt in zip(segs, e.points, strict=True):
                _fix(b, s.start, pt)
        case Slot():
            _slot(b, e)
        case Path():
            _path(b, e)


def _line(b: Builder, p: Vec2, q: Vec2) -> Seg:
    geo = b.add("line", *p, *q)
    if abs(p[1] - q[1]) < 1e-9:
        b.want("horizontal", geo.name)
    elif abs(p[0] - q[0]) < 1e-9:
        b.want("vertical", geo.name)
    return Seg(f"{geo.name}.start", f"{geo.name}.end", geo)


def _arc(b: Builder, center: Vec2, p: Vec2, q: Vec2, ccw: bool, expr: str | None) -> Seg:
    r = math.dist(center, p)
    lo, hi = (p, q) if ccw else (q, p)
    a0 = math.atan2(lo[1] - center[1], lo[0] - center[0])
    a1 = math.atan2(hi[1] - center[1], hi[0] - center[0])
    geo = b.add("arc", *center, r, a0, a1 if a1 > a0 else a1 + 2 * math.pi)
    b.want("radius", geo.name, value=r, expr=expr)
    start, end = f"{geo.name}.start", f"{geo.name}.end"
    return Seg(start, end, geo) if ccw else Seg(end, start, geo)


def _chain(b: Builder, segs: list[Seg]) -> None:
    for s, t in zip(segs, segs[1:] + segs[:1], strict=True):
        b.want("coincident", s.end, t.start)
        if "arc" not in (s.geo.kind, t.geo.kind):
            continue
        first, second = (s, t) if s.geo.kind == "line" or t.geo.kind == "arc" else (t, s)
        at = s.end if s.geo.kind == "arc" else t.start
        tangent = Constraint(kind="tangent", refs=[first.geo.name, second.geo.name, at])
        if abs(_residual(tangent, np.array(b.x0), b.geos)[0]) < 1e-6:
            b.wanted.append(tangent)


def _fix(b: Builder, ref: str, pt: tuple[Expr, Expr]) -> None:
    b.want("distance_x", ref, value=b.num(pt[0]), expr=_t(pt[0]))
    b.want("distance_y", ref, value=b.num(pt[1]), expr=_t(pt[1]))


def _fallback(b: Builder, segs: list[Seg]) -> None:
    for s in segs:
        for ref in (s.start, s.end, *([f"{s.geo.name}.center"] if s.geo.kind == "arc" else [])):
            px, py = b.at(ref)
            b.want("distance_x", ref, value=float(px))
            b.want("distance_y", ref, value=float(py))


def _rect(b: Builder, e: Rect) -> None:
    cx, cy, w, h, r = (b.num(v) for v in (*e.center, e.width, e.height, e.corner_radius))
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    k = max(r, 0.0)
    sides = [((x0 + k, y0), (x1 - k, y0)), ((x1, y0 + k), (x1, y1 - k)), ((x1 - k, y1), (x0 + k, y1)), ((x0, y1 - k), (x0, y0 + k))]
    corners = [(x1 - k, y0 + k), (x1 - k, y1 - k), (x0 + k, y1 - k), (x0 + k, y0 + k)]
    segs: list[Seg] = []
    lines: list[Seg] = []
    for (p, q), c, nxt in zip(sides, corners, sides[1:] + sides[:1], strict=True):
        lines.append(_line(b, p, q))
        segs += [lines[-1], *([_arc(b, c, q, nxt[0], True, _t(e.corner_radius))] if k > 0 else [])]
    _chain(b, segs)
    bottom, right, top, left = lines
    b.want("distance_x", left.end, right.start, value=w, expr=_t(e.width))
    b.want("distance_y", bottom.start, top.start, value=h, expr=_t(e.height))
    b.want("distance_x", left.end, value=x0, expr=f"{_t(e.center[0])} - {_t(e.width)} / 2")
    b.want("distance_y", bottom.start, value=y0, expr=f"{_t(e.center[1])} - {_t(e.height)} / 2")
    _fallback(b, segs)


def _slot(b: Builder, e: Slot) -> None:
    cx, cy, length, width, angle = (b.num(v) for v in (*e.center, e.length, e.width, e.angle))
    ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    d, r = (length - width) / 2, width / 2
    c1, c2 = (cx - d * ux, cy - d * uy), (cx + d * ux, cy + d * uy)

    def side(c: Vec2, k: float) -> Vec2:
        return (c[0] - k * r * uy, c[1] + k * r * ux)

    half = f"{_t(e.width)} / 2"
    segs = [
        _line(b, side(c1, -1), side(c2, -1)),
        _arc(b, c2, side(c2, -1), side(c2, 1), True, half),
        _line(b, side(c2, 1), side(c1, 1)),
        _arc(b, c1, side(c1, 1), side(c1, -1), True, half),
    ]
    _chain(b, segs)
    centers = (f"{segs[3].geo.name}.center", f"{segs[1].geo.name}.center")
    b.want("distance", *centers, value=length - width, expr=f"{_t(e.length)} - {_t(e.width)}")
    b.want("angle", segs[0].geo.name, value=angle, expr=_t(e.angle))
    half_span = f"({_t(e.length)} - {_t(e.width)}) / 2"
    b.want("distance_x", f"{segs[3].geo.name}.center", value=c1[0], expr=f"{_t(e.center[0])} - {half_span} * cos({_t(e.angle)})")
    b.want("distance_y", f"{segs[3].geo.name}.center", value=c1[1], expr=f"{_t(e.center[1])} - {half_span} * sin({_t(e.angle)})")
    _fallback(b, segs)


def _path(b: Builder, e: Path) -> None:
    given = [e.start, *(s.to for s in e.segments)]
    pts = [(b.num(x), b.num(y)) for x, y in given]
    closed = math.dist(pts[0], pts[-1]) < 1e-9
    kinds = [(s.arc, s.radius) for s in e.segments] + ([] if closed else [("none", None)])
    pts, given = (pts[:-1], given[:-1]) if closed else (pts, given)
    n = len(pts)
    fillet: list[Expr] = [0.0] * n
    for i, s in enumerate(e.segments):
        fillet[(i + 1) % n] = s.fillet
    trims = [_corner(pts, j, b.num(fillet[j])) if b.num(fillet[j]) > 0 else None for j in range(n)]
    segs: list[Seg] = []
    outgoing: list[Seg] = []
    for i, (arc, radius) in enumerate(kinds):
        j = (i + 1) % n
        before, after = trims[i], trims[j]
        if arc != "none" and (before or after):
            raise UnsupportedSketchError("a fillet next to an arc segment is not analysed")
        p = before[2] if before else pts[i]
        q = after[1] if after else pts[j]
        if arc == "none":
            outgoing.append(_line(b, p, q))
        else:
            r = b.num(radius) if radius is not None else 0.0
            outgoing.append(_arc(b, _arc_center(p, q, r, arc == "cw"), p, q, arc == "ccw", _t(radius) if radius is not None else None))
        segs.append(outgoing[-1])
        if after:
            segs.append(_arc(b, after[0], after[1], after[2], after[3], _t(fillet[j])))
    _chain(b, segs)
    for j, pt in enumerate(given):
        if trims[j]:
            vertex = b.add("point", *pts[j])
            _fix(b, vertex.name, pt)
            b.want("point_on_object", vertex.name, outgoing[j - 1].geo.name)
            b.want("point_on_object", vertex.name, outgoing[j].geo.name)
        else:
            _fix(b, outgoing[j].start, pt)
    _fallback(b, segs)


def _corner(pts: list[Vec2], j: int, f: float) -> tuple[Vec2, Vec2, Vec2, bool]:
    v = np.array(pts[j])
    u1, u2 = _unit(np.array(pts[j - 1]) - v), _unit(np.array(pts[(j + 1) % len(pts)]) - v)
    half = math.acos(float(np.clip(np.dot(u1, u2), -1, 1))) / 2
    t1, t2 = v + u1 * f / math.tan(half), v + u2 * f / math.tan(half)
    c = v + _unit(u1 + u2) * f / math.sin(half)
    a, b = t1 - c, t2 - c
    ccw = float(a[0] * b[1] - a[1] * b[0]) > 0
    return (float(c[0]), float(c[1])), (float(t1[0]), float(t1[1])), (float(t2[0]), float(t2[1])), ccw


def _arc_center(p: Vec2, q: Vec2, r: float, cw: bool) -> Vec2:
    dx, dy = q[0] - p[0], q[1] - p[1]
    chord = math.hypot(dx, dy)
    h = math.sqrt(max(r * r - chord * chord / 4, 0.0)) / chord
    k = 1 if cw else -1
    return ((p[0] + q[0]) / 2 + k * h * dy, (p[1] + q[1]) / 2 - k * h * dx)


def _t(e: Expr) -> str:
    return repr(float(e)) if isinstance(e, int | float) else e if e.isidentifier() else f"({e})"
