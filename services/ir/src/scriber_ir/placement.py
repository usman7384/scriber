import math

from scriber_ir.expr import evaluate
from scriber_ir.model import GridPattern, Hole, PolarPattern

Point2 = tuple[float, float]


def hole_centres(hole: Hole, values: dict[str, float]) -> list[Point2]:
    def v(e: float | str) -> float:
        return evaluate(e, values)

    at = hole.at
    if isinstance(at, GridPattern):
        nx, ny = round(v(at.count_x)), round(v(at.count_y))
        cx, cy, sx, sy = v(at.center[0]), v(at.center[1]), v(at.spacing_x), v(at.spacing_y)
        return [(cx + (i - (nx - 1) / 2) * sx, cy + (j - (ny - 1) / 2) * sy) for i in range(nx) for j in range(ny)]
    if isinstance(at, PolarPattern):
        n, r, a0 = round(v(at.count)), v(at.diameter) / 2, v(at.start_angle)
        cx, cy = v(at.center[0]), v(at.center[1])
        return [(cx + r * math.cos(math.radians(a0 + 360 * k / n)), cy + r * math.sin(math.radians(a0 + 360 * k / n))) for k in range(n)]
    return [(v(x), v(y)) for x, y in at.points]
