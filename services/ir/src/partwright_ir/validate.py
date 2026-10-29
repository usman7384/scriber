import math
from collections.abc import Iterator

from pydantic import BaseModel

from partwright_ir.expr import ExprError, evaluate, names
from partwright_ir.fasteners import hole_size, parse
from partwright_ir.model import (
    FACE_NAMES,
    AirfoilSection,
    Circle,
    Design,
    Entity,
    Expr,
    Extrude,
    Feature,
    Hole,
    Loft,
    Part,
    Path,
    Pattern,
    PlaneRef,
    Polygon,
    Provenance,
    Rect,
    Revolve,
    Selector,
    Sketch,
    Slot,
)
from partwright_ir.placement import hole_centres

BASE_PLANES = ("XY", "XZ", "YZ")
DRILL_AXIS = {"XY": "Z", "XZ": "Y", "YZ": "X"}
NON_EXPR_FIELDS = {
    *("id", "name", "intent", "sketch", "kind", "mode", "axis", "edges", "base", "ref", "of", "normal", "parallel"),
    *("convexity", "extreme", "type", "fastener", "fit", "drill_point", "thread", "extent", "arc", "direction"),
    *("rotate_about", "process", "features", "mirror_plane", "material", "naca", "sections"),
}
POSITIVE_FIELDS = {
    *("width", "height", "diameter", "length", "radius", "thickness", "count", "count_x", "count_y"),
    *("cb_diameter", "cb_depth", "cs_diameter", "cs_angle", "depth", "chord"),
}
PATTERNABLE = (Extrude, Revolve, Hole, Loft)


class IrError(BaseModel):
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def validate(design: Design) -> list[IrError]:
    part_errors = [e for i, p in enumerate(design.parts) for e in _part_errors(design, p, f"parts[{i}]")]
    errors = [*_param_errors(design), *part_errors, *_unused_params(design)]
    if errors:
        return errors
    return [e for i, p in enumerate(design.parts) for e in _overlapping_holes(design, p, f"parts[{i}]")]


def used_params(design: Design) -> set[str]:
    return {n for part in design.parts for node in [*part.datums, *part.sketches, *part.features] for n in _names(node)}


def _param_errors(design: Design) -> Iterator[IrError]:
    seen: set[str] = set()
    for p in design.params:
        if p.name in seen:
            yield IrError(path=f"params.{p.name}", message="duplicate parameter name")
        seen.add(p.name)
        if (p.min is not None and p.value < p.min) or (p.max is not None and p.value > p.max):
            yield IrError(path=f"params.{p.name}", message=f"value {p.value} outside [{p.min}, {p.max}]")


def _unused_params(design: Design) -> Iterator[IrError]:
    used = used_params(design)
    for p in design.params:
        if p.name not in used:
            yield IrError(
                path=f"params.{p.name}", message="defined but not used; reference it in feature expressions instead of a literal number"
            )


def _part_errors(design: Design, part: Part, path: str) -> Iterator[IrError]:
    values = design.param_values()
    sketches = {s.id: s for s in part.sketches}
    datums = [d.id for d in part.datums]
    for label, ids in (("sketch", [s.id for s in part.sketches]), ("feature", [f.id for f in part.features]), ("datum", datums)):
        if len(set(ids)) != len(ids):
            yield IrError(path=path, message=f"duplicate {label} id")
    for d in part.datums:
        yield from _exprs(d, values, f"{path}.datums.{d.id}")
    for s in part.sketches:
        yield from _exprs(s, values, f"{path}.sketches.{s.id}")
    first = next((f for f in part.features if not isinstance(f, AirfoilSection)), part.features[0])
    if not (isinstance(first, Loft) or (isinstance(first, Extrude | Revolve) and first.mode == "add")):
        yield IrError(path=f"{path}.features[0]", message="first feature must be an additive extrude or revolve")
    seen: dict[str, Feature] = {}
    for f in part.features:
        where = f"{path}.features.{f.id}"
        yield from _feature_errors(f, sketches, datums, seen, values, where)
        yield from _exprs(f, values, where)
        seen[f.id] = f
    yield from _face_group_errors(part, seen, path)
    used = {f.sketch for f in part.features if isinstance(f, Extrude | Revolve)}
    for sid in sketches:
        if sid not in used:
            msg = "is not used by any extrude or revolve; holes must be hole features, so delete it or use it"
            yield IrError(path=f"{path}.sketches.{sid}", message=msg)


def _feature_errors(
    f: Feature, sketches: dict[str, Sketch], datums: list[str], seen: dict[str, Feature], values: dict[str, float], path: str
) -> Iterator[IrError]:
    match f:
        case Extrude() | Revolve():
            sketch = sketches.get(f.sketch)
            if sketch is None:
                yield IrError(path=path, message=f"unknown sketch {f.sketch!r}; known: {list(sketches)}")
            else:
                yield from _ref_errors(sketch.plane, datums, seen, path)
            if isinstance(f, Extrude):
                yield from _extent_errors(f, bool(seen), path)
            elif sketch is not None:
                yield from _revolve_errors(f, sketch, values, path)
        case Hole():
            yield from _ref_errors(f.plane, datums, seen, path)
            yield from _hole_errors(f, path)
        case Pattern():
            yield from _pattern_errors(f, seen, sketches, path)
        case AirfoilSection():
            yield from _ref_errors(f.plane, datums, seen, path)
            yield from _naca_errors(f.naca, path)
        case Loft():
            yield from _loft_errors(f, seen, path)
        case _:
            selectors = [f.edges] if hasattr(f, "edges") else list(getattr(f, "open", []))
            yield from (e for s in selectors for e in _selector_errors(s, seen, path))


def _ref_errors(plane: PlaneRef, datums: list[str], seen: dict[str, Feature], path: str) -> Iterator[IrError]:
    ref = plane.ref
    if ref in BASE_PLANES or ref in datums:
        return
    owner, _, face = ref.partition(".")
    if not face:
        yield IrError(path=path, message=f"unknown plane {ref!r}; use XY, XZ, YZ, a datum id {datums} or '<feature>.<face>'")
    elif owner != "part" and owner not in seen:
        yield IrError(path=path, message=f"plane {ref!r} refers to {owner!r}, which is not an earlier feature")
    elif isinstance(seen.get(owner), AirfoilSection):
        yield IrError(path=path, message=f"plane {ref!r} refers to an airfoil section; use the loft through it")
    elif face not in FACE_NAMES:
        yield IrError(path=path, message=f"unknown face {face!r} in {ref!r}; use one of {', '.join(FACE_NAMES)}")
    elif face in ("start", "end") and not isinstance(seen.get(owner), Extrude):
        yield IrError(path=path, message=f"{ref!r}: start and end faces exist only on extrudes")


def _extent_errors(f: Extrude, has_part: bool, path: str) -> Iterator[IrError]:
    if f.extent in ("blind", "symmetric", "two_sided") and f.distance is None:
        yield IrError(path=path, message=f"extent {f.extent!r} needs a distance")
    if f.extent == "two_sided" and f.distance2 is None:
        yield IrError(path=path, message="extent 'two_sided' needs distance2 for the second side")
    if f.extent == "two_sided" and f.distance2 is not None and not isinstance(f.distance2, str) and f.distance2 <= 0:
        yield IrError(path=path, message="distance2 must be > 0")
    if f.extent == "through_all" and f.mode == "add":
        yield IrError(path=path, message="extent 'through_all' only makes sense for cut or intersect")
    if f.extent == "up_to_next" and not has_part:
        yield IrError(path=path, message="extent 'up_to_next' needs an earlier feature to stop at")


def _hole_errors(h: Hole, path: str) -> Iterator[IrError]:
    if h.fastener is None and h.diameter is None:
        yield IrError(path=path, message="give the hole a fastener (e.g. 'M6') or a diameter")
    if h.fastener is not None and parse(h.fastener) is None:
        yield IrError(path=path, message=f"unknown fastener {h.fastener!r}; use M2 to M30, optionally with a pitch such as M18x1.5")
    if h.type == "tapped" and h.fastener is None:
        yield IrError(path=path, message="a tapped hole needs a fastener such as 'M6'")
    if h.type == "counterbore" and h.fastener is None and (h.cb_diameter is None or h.cb_depth is None):
        yield IrError(path=path, message="a counterbore needs a fastener or both cb_diameter and cb_depth")
    if h.type == "countersink" and h.fastener is None and h.cs_diameter is None:
        yield IrError(path=path, message="a countersink needs a fastener or cs_diameter")
    if h.type != "counterbore" and (h.cb_diameter is not None or h.cb_depth is not None):
        yield IrError(path=path, message="cb_diameter and cb_depth need type 'counterbore'")
    if h.type != "countersink" and h.cs_diameter is not None:
        yield IrError(path=path, message="cs_diameter needs type 'countersink'")
    if h.drill_point == "118" and h.depth is None:
        yield IrError(path=path, message="a drill point only applies to a blind hole with a depth")


def _pattern_errors(p: Pattern, seen: dict[str, Feature], sketches: dict[str, Sketch], path: str) -> Iterator[IrError]:
    usable = [fid for fid, f in seen.items() if isinstance(f, PATTERNABLE)]
    for fid in p.features:
        source = seen.get(fid)
        if source is None:
            what = "a sketch; list the feature that uses it" if fid in sketches else "not an earlier feature"
            yield IrError(path=path, message=f"pattern source {fid!r} is {what}; patternable features so far: {usable}")
        elif not isinstance(source, PATTERNABLE):
            yield IrError(
                path=path, message=f"pattern source {fid!r} is a {source.kind}; only extrudes, revolves and holes can be patterned"
            )
    if p.type == "linear" and p.spacing is None:
        yield IrError(path=path, message="a linear pattern needs a spacing")


def _naca_errors(code: str, path: str) -> Iterator[IrError]:
    if code[2:] == "00":
        yield IrError(path=path, message=f"NACA {code} has zero thickness")
    if (code[0] == "0") != (code[1] == "0"):
        yield IrError(path=path, message=f"NACA {code}: camber and its position must both be zero or both be set")


def _loft_errors(f: Loft, seen: dict[str, Feature], path: str) -> Iterator[IrError]:
    sections = [fid for fid, s in seen.items() if isinstance(s, AirfoilSection)]
    for sid in f.sections:
        if sid not in sections:
            yield IrError(path=path, message=f"loft section {sid!r} is not an earlier airfoil_section; sections so far: {sections}")


def _revolve_errors(f: Revolve, sketch: Sketch, values: dict[str, float], path: str) -> Iterator[IrError]:
    axis = 0 if f.axis == "Y" else 1
    try:
        offset = evaluate(f.axis_offset, values)
        spans = [_span(e, axis, values) for e in sketch.entities]
    except ExprError:
        return  # the bad expression is reported where it is written
    for lo, hi in spans:
        if lo < offset - 1e-6 and hi > offset + 1e-6:
            fix = (
                "draw half the section on one side of it; for a plain cylinder or boss use "
                f'{{"kind": "extrude", "id": "{f.id}", "name": "{f.name}", "sketch": "{sketch.id}", "distance": <height>}} instead'
            )
            yield IrError(path=path, message=f"the sketch {sketch.id!r} crosses the revolve axis; {fix}")
            return


def _span(e: Entity, axis: int, values: dict[str, float]) -> tuple[float, float]:
    match e:
        case Circle() | Rect() | Slot():
            c = evaluate(e.center[axis], values)
            return c - _half(e, axis, values), c + _half(e, axis, values)
        case Polygon():
            xs = [evaluate(p[axis], values) for p in e.points]
        case Path():
            xs = [evaluate(e.start[axis], values), *(evaluate(s.to[axis], values) for s in e.segments)]
    return min(xs), max(xs)


def _half(e: Circle | Rect | Slot, axis: int, values: dict[str, float]) -> float:
    if isinstance(e, Circle):
        return evaluate(e.diameter, values) / 2
    if isinstance(e, Rect):
        return evaluate(e.width if axis == 0 else e.height, values) / 2
    return evaluate(e.length, values) / 2


def _selector_errors(s: Selector, seen: dict[str, Feature], path: str) -> Iterator[IrError]:
    if s.of != "part" and s.of not in seen:
        yield IrError(path=path, message=f"selector refers to {s.of!r}, which is not an earlier feature")
    elif isinstance(seen.get(s.of), AirfoilSection):
        yield IrError(path=path, message=f"selector refers to the airfoil section {s.of!r}; select from the loft through it")


def _face_group_errors(part: Part, seen: dict[str, Feature], path: str) -> Iterator[IrError]:
    given = [g.name for g in part.face_groups]
    if len(set(given)) != len(given):
        yield IrError(path=f"{path}.face_groups", message="duplicate face group name")
    for g in part.face_groups:
        yield from _selector_errors(g.faces, seen, f"{path}.face_groups.{g.name}")


def _overlapping_holes(design: Design, part: Part, path: str) -> Iterator[IrError]:
    values = design.param_values()
    holes = [
        (f, c, hole_size(f, values).diameter, _depth_range(f, values))
        for f in part.features
        if isinstance(f, Hole)
        for c in hole_centres(f, values)
    ]
    for i, (a, ca, da, ra) in enumerate(holes):
        for b, cb, db, rb in holes[i + 1 :]:
            gap = math.dist(ca, cb)
            same_plane = a.plane.ref == b.plane.ref
            if same_plane and gap > 1e-6 and gap < (da + db) / 2 - 1e-6 and ra[0] < rb[1] and rb[0] < ra[1]:
                where = f"{a.id!r} at ({ca[0]:g}, {ca[1]:g}) and {b.id!r} at ({cb[0]:g}, {cb[1]:g})"
                axis = DRILL_AXIS.get(a.plane.ref)
                plane = f"both on plane {a.plane.ref}" + (f", drilling along {axis}" if axis else "")
                message = f"holes {where} overlap at the same depth ({plane}); spread them apart or put each on the face it belongs to"
                yield IrError(path=f"{path}.features.{a.id}", message=message)
                return


def _depth_range(hole: Hole, values: dict[str, float]) -> tuple[float, float]:
    if hole.depth is None:
        return (-math.inf, math.inf)
    top = evaluate(hole.plane.offset, values)
    return (top - evaluate(hole.depth, values), top)


def _names(node: BaseModel) -> Iterator[str]:
    for name, value in node:
        if isinstance(value, Provenance) or name in NON_EXPR_FIELDS:
            continue
        if isinstance(value, BaseModel):
            yield from _names(value)
        elif isinstance(value, list | tuple):
            for item in value:
                yield from _names(item) if isinstance(item, BaseModel) else _item_names(item)
        else:
            yield from _item_names(value)


def _item_names(value: object) -> Iterator[str]:
    if isinstance(value, list | tuple):
        for v in value:
            yield from _item_names(v)
    elif isinstance(value, str):
        try:
            yield from names(value)
        except ExprError:
            return


def _exprs(node: BaseModel, values: dict[str, float], path: str) -> Iterator[IrError]:
    for name, value in node:
        sub = f"{path}.{name}"
        if isinstance(value, Provenance) or name in NON_EXPR_FIELDS:
            continue
        if isinstance(value, BaseModel):
            yield from _exprs(value, values, sub)
        elif isinstance(value, list | tuple):
            for i, item in enumerate(value):
                if isinstance(item, BaseModel):
                    yield from _exprs(item, values, f"{sub}[{i}]")
                elif isinstance(item, tuple | list):
                    yield from (e for j, x in enumerate(item) for e in _expr(x, values, f"{sub}[{i}][{j}]", False))
                else:
                    yield from _expr(item, values, f"{sub}[{i}]", False)
        elif isinstance(value, float | int | str) and not isinstance(value, bool):
            yield from _expr(value, values, sub, name in POSITIVE_FIELDS, name in ("distance", "spacing"))


def _expr(value: Expr, values: dict[str, float], path: str, positive: bool, nonzero: bool = False) -> Iterator[IrError]:
    try:
        result = evaluate(value, values)
    except ExprError as e:
        yield IrError(path=path, message=str(e))
        return
    if positive and result <= 0:
        yield IrError(path=path, message=f"must be > 0, got {result:g}")
    if nonzero and result == 0:
        yield IrError(path=path, message="must not be 0")
