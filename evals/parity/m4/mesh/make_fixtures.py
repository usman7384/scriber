import json
import math
from pathlib import Path

from build123d import BuildSketch, Circle, Part, Polygon, Pos, export_stl, extrude, fillet, insert, offset

HERE = Path(__file__).parent
MOUNTS = [(-50.0, -25.0), (50.0, -25.0), (-50.0, 25.0), (50.0, 25.0)]
MOUNT_D, HUB_D, THICK = 6.6, 10.0, 8.0
Pt = tuple[float, float]


def bar(a: Pt, b: Pt, wa: float, wb: float) -> Polygon:
    n = math.dist(a, b)
    px, py = (a[1] - b[1]) / n, (b[0] - a[0]) / n
    pts = [(a[0] + px * wa / 2, a[1] + py * wa / 2), (b[0] + px * wb / 2, b[1] + py * wb / 2)]
    pts += [(b[0] - px * wb / 2, b[1] - py * wb / 2), (a[0] - px * wa / 2, a[1] - py * wa / 2)]
    return Polygon(*pts, align=None)


def to_bracket() -> Part:
    (a, b, c, d) = MOUNTS
    bars = [bar(a, b, 9, 9), bar(c, d, 9, 9), bar(a, c, 7, 7), bar(b, d, 7, 7), *(bar(m, (0, 0), 10, 7) for m in MOUNTS)]
    with BuildSketch() as truss:
        insert([Pos(*m) * Circle(9) for m in MOUNTS] + [Circle(12), *bars])
    # closing (grow then shrink) blends every bar junction with an R4 web, the look of a topology-optimised truss
    organic = offset(offset(truss.sketch, 4), -4)
    organic = organic - [Pos(*m) * Circle(MOUNT_D / 2) for m in MOUNTS] - Circle(HUB_D / 2)
    part = fillet(extrude(organic, THICK).edges(), radius=1.2)
    return Pos(0, 0, -part.bounding_box().min.Z) * part


def main() -> None:
    export_stl(to_bracket(), HERE / "to_bracket.stl", tolerance=0.1, angular_tolerance=0.8)
    truth = {"holes": [{"center": list(m), "diameter": MOUNT_D} for m in MOUNTS], "thickness": THICK}
    (HERE / "to_bracket.json").write_text(json.dumps(truth, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
