from typing import Any

from build123d import Compound, Face, Location, Shape, Vector, Vertex

TESSELLATION_MM = 0.05
ON_FACE_MM = 1e-3


# Each face of the placed part belongs to the earliest feature after which some face already held that spot.
def part_structure(snapshots: list[tuple[str, Shape[Any]]], placed: Shape[Any]) -> dict[str, Any]:
    local = snapshots[-1][1].faces()
    surfaces = [(fid, Compound(shape.faces())) for fid, shape in snapshots]
    owners: dict[str, list[int]] = {}
    meshes = []
    for i, (face, world) in enumerate(zip(local, placed.faces(), strict=True)):
        point = _on_face(face)
        owner = next((fid for fid, s in surfaces if s.distance_to(point) < ON_FACE_MM), snapshots[-1][0])
        owners.setdefault(owner, []).append(i)
        meshes.append(_mesh(world))
    return {"faces": meshes, "features": owners, "placement": _matrix(placed.location)}


def _on_face(face: Face) -> Vertex:
    vertices, triangles = face.tessellate(TESSELLATION_MM)
    a, b, c = (vertices[k] for k in max(triangles, key=lambda t: _area(vertices, t)))
    # the centroid sits within chord error of a curved face; the closest point on the face is exactly on it
    _, _, on = face.distance_to_with_closest_points(Vertex(*((a + b + c) / 3)))
    return Vertex(*on)


def _area(v: list[Vector], t: tuple[int, int, int]) -> float:
    return float((v[t[1]] - v[t[0]]).cross(v[t[2]] - v[t[0]]).length)


def _mesh(face: Face) -> dict[str, list[float] | list[int]]:
    vertices, triangles = face.tessellate(TESSELLATION_MM)
    return {
        "positions": [round(c, 4) for v in vertices for c in (v.X, v.Y, v.Z)],
        "indices": [k for t in triangles for k in t],
    }


def _matrix(location: Location | None) -> list[float]:
    matrix = (location or Location()).wrapped.Transformation()
    return [matrix.Value(r, c) for r in (1, 2, 3) for c in (1, 2, 3, 4)]
