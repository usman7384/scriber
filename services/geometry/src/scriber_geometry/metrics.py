import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from build123d import GeomType, Location, Shape, Vector
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepGProp import BRepGProp
from OCP.BRepTools import BRepTools
from OCP.GProp import GProp_GProps

from scriber_geometry.models import HoleInfo, PartMetrics, Placement

# a bore cut by keys, a keyway or a flat keeps arcs over five sixths of a turn at one depth; a pocket ringed by spokes,
# fillets and slot ends keep less, and arcs at different depths (two pockets on one axis) are not added up
BORE_TURN = 5 / 3 * math.pi


@dataclass(frozen=True)
class ConcaveCylinder:
    radius: float
    axis: Vector
    origin: Vector
    span: float
    heights: list[float]
    point: Vector

    @property
    def bore(self) -> bool:
        return self.span >= BORE_TURN


def part_metrics(part_id: str, shape: Shape[Any]) -> PartMetrics:
    box = shape.bounding_box()
    # OCCT's default integration under-reads B-spline bodies (lofted wings by about 25%); ask for a set accuracy
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, props, 1e-6, True)
    centre = props.CentreOfMass()
    return PartMetrics(
        id=part_id,
        name=shape.label or part_id,
        volume=props.Mass(),
        bbox_min=_t(box.min),
        bbox_size=_t(box.size),
        solids=len(shape.solids()),
        faces=len(shape.faces()),
        valid=shape.is_valid,
        holes=holes(shape),
        center_of_mass=(centre.X(), centre.Y(), centre.Z()),
        placement=placement(shape.location),
    )


def placement(loc: Location | None) -> Placement:
    t = (loc or Location()).wrapped.Transformation()
    r0, r1, r2 = ((t.Value(i, 1), t.Value(i, 2), t.Value(i, 3), t.Value(i, 4)) for i in (1, 2, 3))
    return (r0, r1, r2)


def holes(shape: Shape[Any]) -> list[HoleInfo]:
    out = []
    for c in concave_cylinders(shape):
        if not c.bore:
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
        rings = _rings(faces)
        span = max(sum(s for s, _, _ in ring) for ring in rings)
        bores = [ring for ring in rings if sum(s for s, _, _ in ring) >= BORE_TURN] or rings
        out.append(ConcaveCylinder(radius, d, loc, span, [t for ring in bores for _, ts, _ in ring for t in ts], faces[0][2]))
    return out


def _rings(faces: list[tuple[float, list[float], Vector]]) -> list[list[tuple[float, list[float], Vector]]]:
    # faces whose depth ranges overlap form one ring around the axis
    rings: list[list[tuple[float, list[float], Vector]]] = []
    top = -math.inf
    for face in sorted(faces, key=lambda f: min(f[1])):
        if rings and min(face[1]) < top - 1e-6:
            rings[-1].append(face)
        else:
            rings.append([face])
        top = max(top, max(face[1])) if len(rings[-1]) > 1 else max(face[1])
    return rings


def _t(v: Vector) -> tuple[float, float, float]:
    return (v.X, v.Y, v.Z)
