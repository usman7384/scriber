import argparse
import math
from pathlib import Path
from typing import Any

import httpx
import trimesh

from scriber_cli.pipe import Http, ok, wait

Point = tuple[float, float]


def tool_outline(stl: Path) -> tuple[list[Point], float]:
    # the outer loop of a mid-height section: right for tools that are flat along Z, not for a full silhouette
    mesh = trimesh.load_mesh(stl)
    z0, z1 = float(mesh.bounds[0][2]), float(mesh.bounds[1][2])
    section = mesh.section(plane_origin=[0, 0, (z0 + z1) / 2], plane_normal=[0, 0, 1])
    if section is None:
        raise ValueError(f"{stl.name}: no section at half height")
    loop = max(section.discrete, key=lambda p: abs(_area([(float(x), float(y)) for x, y, _ in p])))
    points = [(float(x), float(y)) for x, y, _ in loop[:-1]]
    return _ccw(_drop_collinear(points)), z1 - z0


def pocket_path(outline: list[Point]) -> dict[str, Any]:
    # outline offset outward by `offset`: miters at concave corners, arcs of radius `offset` around convex ones
    n = len(outline)
    segments: list[dict[str, Any]] = []
    for i, p in enumerate(outline):
        a, b = _normal(outline[i - 1], p), _normal(p, outline[(i + 1) % n])
        if _cross(_sub(p, outline[i - 1]), _sub(outline[(i + 1) % n], p)) > 0:
            segments += [{"to": _at(p, a)}, {"to": _at(p, b), "arc": "ccw", "radius": "offset"}]
        else:
            k = 1 + a[0] * b[0] + a[1] * b[1]
            segments.append({"to": _at(p, ((a[0] + b[0]) / k, (a[1] + b[1]) / k))})
    return {"kind": "path", "start": segments[-1]["to"], "segments": segments}


def insert_design(
    outline: list[Point], tool_height: float, offset: float = 1.0, margin: float = 12.0, floor: float = 4.0
) -> dict[str, Any]:
    xs, ys = [p[0] for p in outline], [p[1] for p in outline]
    center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    size = (max(xs) - min(xs), max(ys) - min(ys))
    tool = {"source": "document", "ref": "tool.stl"}
    return {
        "title": "Shadow box insert",
        "params": [
            {"name": "offset", "value": offset, "unit": "mm", "min": 0.2, "max": 5, "description": "gap between tool and pocket wall"},
            {"name": "pocket_depth", "value": round(tool_height, 4), "unit": "mm", "description": "tool thickness", "provenance": tool},
            {"name": "floor", "value": floor, "unit": "mm", "description": "material under the pocket"},
            {"name": "margin", "value": margin, "unit": "mm", "description": "border around the pocket"},
            {"name": "body_length", "value": round(size[0], 4), "unit": "mm", "description": "tool length", "provenance": tool},
            {"name": "body_width", "value": round(size[1], 4), "unit": "mm", "description": "tool width", "provenance": tool},
        ],
        "parts": [
            {
                "id": "insert",
                "name": "Insert",
                "sketches": [
                    {
                        "id": "block",
                        "entities": [
                            {"kind": "rect", "center": center, "width": "body_length + 2 * margin", "height": "body_width + 2 * margin"}
                        ],
                    },
                    {"id": "pocket", "plane": {"offset": "floor + pocket_depth"}, "entities": [pocket_path(outline)]},
                ],
                "features": [
                    {"kind": "extrude", "id": "body", "name": "Insert", "sketch": "block", "distance": "floor + pocket_depth"},
                    {
                        "kind": "extrude",
                        "id": "tool_pocket",
                        "name": "Tool pocket",
                        "intent": "tool outline offset by the clearance",
                        "sketch": "pocket",
                        "mode": "cut",
                        "distance": "-pocket_depth",
                    },
                ],
            }
        ],
    }


def submit(http: Http, project: str, design: dict[str, Any], prompt: str) -> dict[str, Any]:
    return wait(http, ok(http.post(f"/projects/{project}/designs", json={"design": design, "prompt": prompt})))


def _at(p: Point, n: Point) -> tuple[str, str]:
    return (f"{p[0]:.6f} + offset * {n[0]:.9f}", f"{p[1]:.6f} + offset * {n[1]:.9f}")


def _normal(a: Point, b: Point) -> Point:
    dx, dy = _sub(b, a)
    length = math.hypot(dx, dy)
    return (dy / length, -dx / length)


def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _area(points: list[Point]) -> float:
    return sum(_cross(points[i - 1], p) for i, p in enumerate(points)) / 2


def _ccw(points: list[Point]) -> list[Point]:
    return points if _area(points) > 0 else points[::-1]


def _drop_collinear(points: list[Point], tol: float = 1e-6) -> list[Point]:
    n = len(points)
    return [p for i, p in enumerate(points) if abs(_cross(_sub(p, points[i - 1]), _sub(points[(i + 1) % n], p))) > tol]


def main() -> None:
    p = argparse.ArgumentParser(description="Shadow-box insert with a pocket around a tool STL")
    p.add_argument("stl", type=Path)
    p.add_argument("--offset", type=float, default=1.0)
    p.add_argument("--api", default="http://127.0.0.1:8000")
    p.add_argument("--token")
    p.add_argument("--project", required=True)
    p.add_argument("--out", type=Path, default=Path("insert.step"))
    args = p.parse_args()
    outline, height = tool_outline(args.stl)
    headers = {"X-API-Token": args.token} if args.token else {}
    with httpx.Client(base_url=args.api, headers=headers, timeout=30) as http:
        job = submit(http, args.project, insert_design(outline, height, args.offset), f"shadow box for {args.stl.name}")
        if job["status"] != "done":
            raise SystemExit(f"build failed: {job['error']}")
        step = http.get(f"/models/{job['model_id']}/export", params={"fmt": "step"}).raise_for_status()
        args.out.write_bytes(step.content)
    print(f"model {job['model_id']}: {args.out}")


if __name__ == "__main__":
    main()
