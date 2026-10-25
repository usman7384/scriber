import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from build123d import CenterOf, GeomType, Shape, Vector
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepTools import BRepTools

from partwright_geometry.models import HoleInfo, PartMetrics

FULL_TURN = 2 * math.pi - 1e-3


@dataclass(frozen=True)
class ConcaveCylinder:
    radius: float
    axis: Vector
    origin: Vector
    span: float
    heights: list[float]
    point: Vector


def part_metrics(part_id: str, shape: Shape[Any]) -> PartMetrics:
    box = shape.bounding_box()
    return PartMetrics(
        id=part_id,
        name=shape.label or part_id,
        volume=shape.volume,
        bbox_min=_t(box.min),
        bbox_size=_t(box.size),
        solids=len(shape.solids()),
        faces=len(shape.faces()),
        valid=shape.is_valid,
        holes=holes(shape),
        center_of_mass=_t(shape.center(CenterOf.MASS)),
    )


def holes(shape: Shape[Any]) -> list[HoleInfo]:
    out = []
    for c in concave_cylinders(shape):
        if c.span < FULL_TURN:
            continue
        lo, hi = min(c.heights), max(c.heights)
        out.append(HoleInfo(diameter=2 * c.radius, axis=_t(c.axis), center=_t(c.origin + c.axis * ((lo + hi) / 2)), length=hi - lo))
    return sorted(out, key=lambda h: (h.diameter, h.center))


def concave_cylinders(shape: Shape[Any]) -> list[ConcaveCylinder]:
    groups: dict[tuple[float, ...], list[tuple[float, list[float], Vector]]] = defaultdict(list)
    meta: dict[tuple[float, ...], tuple[float, Vector, Vector]] = {}
    for face in shape.faces():
        if face.geom_type != GeomType.CYLINDER:
            continue
        cyl = BRepAdaptor_Surface(face.wrapped).Cylinder()
        radius = cyl.Radius()
        ax = cyl.Axis()
        d = Vector(ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()).normalized()
        if (d.X, d.Y, d.Z) < (0, 0, 0):
            d = -d
        loc = Vector(ax.Location().X(), ax.Location().Y(), ax.Location().Z())
        foot = loc - d * loc.dot(d)
        p = face.center()
        radial = p - (loc + d * (p - loc).dot(d))
        if face.normal_at(p).dot(radial) >= 0:
            continue
        key = (round(radius, 3), *(round(c, 3) for c in (d.X, d.Y, d.Z)), *(round(c, 2) for c in (foot.X, foot.Y, foot.Z)))
        u0, u1, _, _ = BRepTools.UVBounds_s(face.wrapped)
        groups[key].append((u1 - u0, [(Vector(v.X, v.Y, v.Z) - loc).dot(d) for v in face.vertices()], p))
        meta[key] = (radius, d, loc)
    out = []
    for key, faces in groups.items():
        radius, d, loc = meta[key]
        span = sum(s for s, _, _ in faces)
        out.append(ConcaveCylinder(radius, d, loc, span, [t for _, ts, _ in faces for t in ts], faces[0][2]))
    return out


def _t(v: Vector) -> tuple[float, float, float]:
    return (v.X, v.Y, v.Z)
