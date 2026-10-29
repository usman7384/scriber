from collections.abc import Iterator
from dataclasses import dataclass

from partwright_ir.assembly import joint_tree
from partwright_ir.expr import evaluate, names
from partwright_ir.model import Design, Expr, Extrude, Part

Vec = tuple[float, float, float]
Values = dict[str, float]
# a cap plane's position along its axis: a weighted sum of expressions
Terms = list[tuple[Expr, float]]

# build123d base plane normals; Plane.XZ faces -Y
NORMALS: dict[str, Vec] = {"XY": (0, 0, 1), "XZ": (0, -1, 0), "YZ": (1, 0, 0)}
TOLERANCE_MM = 0.01


@dataclass(frozen=True)
class FaceDriver:
    part: str
    feature: str
    param: str
    # mm the face moves along its outward normal per unit of the parameter
    rate: float


def face_driver(design: Design, point: Vec, normal: Vec) -> FaceDriver | None:
    values = design.param_values()
    placed = joint_tree(design)
    found = None
    for part in (p for p in design.parts if p.id not in placed):
        for feature, axis, terms in _caps(part):
            along = _dot(normal, axis)
            if abs(along) < 0.999 or abs(_dot(point, axis) - _position(terms, values)) > TOLERANCE_MM:
                continue
            found = _driver(part.id, feature, terms, values, 1 if along > 0 else -1) or found
    return found


def _caps(part: Part) -> Iterator[tuple[Extrude, Vec, Terms]]:
    datums = {d.id: d for d in part.datums if d.rotate_about == "none"}
    planes = {s.id: s.plane for s in part.sketches}
    for f in part.features:
        plane = planes.get(f.sketch) if isinstance(f, Extrude) else None
        if not isinstance(f, Extrude) or plane is None:
            continue
        datum = datums.get(plane.ref)
        base = datum.base if datum else plane.ref
        if base not in NORMALS:
            continue
        start: Terms = [(plane.offset, 1.0), *([(datum.offset, 1.0)] if datum else [])]
        d, d2 = f.distance or 0.0, f.distance2 or 0.0
        ends: list[Terms] = {
            "blind": [[], [(d, 1.0)]],
            "symmetric": [[(d, -0.5)], [(d, 0.5)]],
            "two_sided": [[(d, 1.0)], [(d2, -1.0)]],
        }.get(f.extent, [[]])
        for end in ends:
            yield f, NORMALS[base], start + end


def _driver(part: str, f: Extrude, terms: Terms, values: Values, side: int) -> FaceDriver | None:
    rates = {name: _rate(terms, values, name) * side for name in values}
    preferred = names(f.distance or 0.0) | names(f.distance2 or 0.0)
    moving = sorted((n for n, r in rates.items() if abs(r) > 1e-9), key=lambda n: (n not in preferred, n))
    return FaceDriver(part, f.id, moving[0], round(rates[moving[0]], 9)) if moving else None


def _position(terms: Terms, values: Values) -> float:
    return sum(k * evaluate(e, values) for e, k in terms)


def _rate(terms: Terms, values: Values, name: str) -> float:
    h = 1e-3 * max(1.0, abs(values[name]))
    up, down = ({**values, name: values[name] + s * h} for s in (1, -1))
    return (_position(terms, up) - _position(terms, down)) / (2 * h)


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
