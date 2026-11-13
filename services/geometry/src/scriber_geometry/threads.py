from typing import Any

from build123d import Face, GeomType, Shape, Vector

from scriber_geometry.models import ThreadInfo

# as the compiled model records a thread: part, on, major, pitch, length, start, axis, radius of the threaded surface
Record = tuple[str, str, float, float, float | None, tuple[float, float, float], tuple[float, float, float], float]


def thread_infos(records: list[Record]) -> dict[str, list[ThreadInfo]]:
    out: dict[str, list[ThreadInfo]] = {}
    for pid, on, major, pitch, length, start, axis, _ in records:
        info = ThreadInfo.model_validate(
            {
                "designation": f"M{major:g}x{pitch:g}",
                "on": on,
                "major": major,
                "pitch": pitch,
                "length": length,
                "start": start,
                "axis": axis,
            }
        )
        out.setdefault(pid, []).append(info)
    return out


def thread_faces(shape: Shape[Any], records: list[Record]) -> dict[str, list[Face]]:
    # threads go into the STEP file as named faces, the way a cosmetic thread travels between CAD systems
    groups: dict[str, list[Face]] = {}
    for i, (_, _, major, pitch, _, start, axis, radius) in enumerate(records):
        faces = [f for f in shape.faces() if _on_thread(f, Vector(*start), Vector(*axis), radius)]
        if faces:
            groups[f"thread_{i + 1}_M{major:g}x{pitch:g}".replace(".", "_")] = faces
    return groups


def _on_thread(face: Face, start: Vector, axis: Vector, radius: float) -> bool:
    line = face.axis_of_rotation
    if face.geom_type != GeomType.CYLINDER or face.radius is None or line is None or abs(face.radius - radius) > 1e-4:
        return False
    offset = start - line.position
    return abs(abs(line.direction.dot(axis)) - 1) < 1e-6 and (offset - line.direction * offset.dot(line.direction)).length < 1e-3
