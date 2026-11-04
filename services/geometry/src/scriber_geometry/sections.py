from pathlib import Path
from typing import Any

from build123d import Face, Plane, Shape, import_step

from scriber_geometry.models import Vec


def span_sections(path: Path, ys: list[float], samples: int = 400) -> list[list[Vec]]:
    shape = import_step(path)
    return [_outline(shape, y, samples) for y in ys]


def _outline(shape: Shape[Any], y: float, samples: int) -> list[Vec]:
    faces = [f for f in shape.intersect(Plane.XZ.offset(-y)) or [] if isinstance(f, Face)]
    if not faces:
        raise ValueError(f"the model has no material at y = {y:g}")
    wire = max(faces, key=lambda f: f.area).outer_wire()
    return [(p.X, p.Y, p.Z) for e in wire.edges() for p in e.positions([i / samples for i in range(samples + 1)])]
