import math
from typing import Any

from build123d import Convexity, Face, GeomType, Plane, Shape, Vector
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepGProp import BRepGProp_Face
from OCP.BRepTools import BRepTools
from OCP.gp import gp_Lin, gp_Pnt, gp_Pnt2d, gp_Vec
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.TopAbs import TopAbs_IN

from partwright_geometry.metrics import concave_cylinders
from partwright_geometry.models import HoleInfo

GRID = 5
RAY_START = 1e-3
# the two sides of a wall face apart within 45 deg; a ray leaving through a neighbouring face turned further is crossing their corner
CORNER_COS = math.cos(math.radians(45))
Sample = tuple[Vector, Vector]
Probe = tuple[float, Vector, str]


def samples(face: Face, n: int = GRID) -> list[Sample]:
    u0, u1, v0, v1 = BRepTools.UVBounds_s(face.wrapped)
    props = BRepGProp_Face(face.wrapped)
    out = []
    for i in range(n):
        for j in range(n):
            u, v = u0 + (i + 0.5) / n * (u1 - u0), v0 + (j + 0.5) / n * (v1 - v0)
            if BRepClass_FaceClassifier(face.wrapped, gp_Pnt2d(u, v), 1e-7).State() != TopAbs_IN:
                continue
            p, normal = gp_Pnt(), gp_Vec()
            props.Normal(u, v, p, normal)
            if normal.Magnitude() > 1e-12:
                out.append((Vector(p), Vector(normal).normalized()))
    return out


def edge_distance(shape: Shape[Any], hole: HoleInfo) -> float | None:
    centre, axis = Vector(*hole.center), Vector(*hole.axis)
    size = 4 * shape.bounding_box().diagonal
    section = shape.intersect(Face.make_rect(size, size, Plane(centre, z_dir=axis)))
    for face in section.faces() if section else []:
        outer = face.outer_wire()
        if Face(outer).distance_to(centre) > 1e-6:
            continue
        if all(e.geom_type == GeomType.CIRCLE and (e.arc_center - centre).length < 1e-3 for e in outer.edges()):
            return None
        return outer.distance_to(centre)
    return None


def thinnest(shape: Shape[Any], limit: float) -> Probe | None:
    # rays stop at the limit since only nearer exits can fail the rule; one intersector keeps each face's search structure
    rays = IntCurvesFace_ShapeIntersector()
    rays.Load(shape.wrapped, 1e-7)
    probes = [(t, p, _describe(f)) for f in shape.faces() for p, n in samples(f) if (t := thickness(rays, f, p, n, limit)) is not None]
    return min(probes, key=lambda x: x[0], default=None)


def thickness(rays: IntCurvesFace_ShapeIntersector, face: Face, point: Vector, normal: Vector, limit: float) -> float | None:
    rays.Perform(gp_Lin(point.to_pnt(), (-normal).to_dir()), RAY_START, limit)
    if rays.NbPnt() == 0:
        return None
    i = min(range(1, rays.NbPnt() + 1), key=rays.WParameter)
    hit = Face(rays.Face(i))
    if _normal(hit, rays.UParameter(i), rays.VParameter(i)).dot(normal) > -CORNER_COS and set(hit.edges()) & set(face.edges()):
        return None
    return float(rays.WParameter(i))


def _normal(face: Face, u: float, v: float) -> Vector:
    p, normal = gp_Pnt(), gp_Vec()
    BRepGProp_Face(face.wrapped).Normal(u, v, p, normal)
    return Vector(normal).normalized()


def internal_corners(shape: Shape[Any]) -> list[Probe]:
    sharp = [
        (0.0, e.center(), "sharp vertical internal edge")
        for e in shape.edges()
        if _vertical_line(e.tangent_at(0.5), e.geom_type) and e.convexity == Convexity.CONCAVE
    ]
    fillets = [
        (c.radius, c.point, f"vertical internal fillet R{c.radius:g}")
        for c in concave_cylinders(shape)
        if not c.bore and abs(c.axis.Z) > 1 - 1e-6
    ]
    return sharp + fillets


def overhangs(shape: Shape[Any]) -> list[Probe]:
    zmin = shape.bounding_box().min.Z
    out = []
    for face in shape.faces():
        planar = face.geom_type == GeomType.PLANE
        if planar and face.bounding_box().max.Z - zmin < 1e-6:
            continue
        points = [(face.center(), face.normal_at())] if planar else samples(face)
        down = [(math.degrees(math.asin(min(1.0, -n.Z))), p) for p, n in points if n.Z < 0]
        if down:
            angle, point = max(down, key=lambda x: x[0])
            out.append((angle, point, _describe(face)))
    return out


def _vertical_line(tangent: Vector, kind: GeomType) -> bool:
    return kind == GeomType.LINE and abs(tangent.Z) > 1 - 1e-6


def _describe(face: Face) -> str:
    kind = f"{face.geom_type.name.lower()} face, area {face.area:.1f} mm²"
    if face.geom_type != GeomType.PLANE:
        return kind
    n = face.normal_at()
    return f"{kind}, normal ({n.X:.2f}, {n.Y:.2f}, {n.Z:.2f})"
