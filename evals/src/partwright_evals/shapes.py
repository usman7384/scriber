from typing import Literal

import numpy as np
import trimesh
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

from partwright_geometry import Artifact

LEVELS = np.linspace(0.05, 0.95, 10)
Array = NDArray[np.float64]


class ShapeCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["teeth", "parts", "mates"]
    description: str
    count: int
    value: float | None = None
    tolerance: float = 0.2


def shape_check(c: ShapeCheck, art: Artifact) -> tuple[bool, str]:
    if c.kind == "parts":
        return len(art.parts) == c.count, f"{len(art.parts)} parts"
    if c.kind == "mates":
        a = art.assembly
        if a is None:
            return False, "no assembly"
        broken, overlaps = a.broken_mates(), a.overlaps()
        return len(a.mates) == c.count and not broken and not overlaps, f"{len(a.mates)} mates, broken {broken}, {len(overlaps)} overlaps"
    found = toothed_rings(trimesh.load_mesh(art.files["stl"], force="mesh"))
    hit = any(n == c.count and c.value is not None and abs(d - c.value) <= c.tolerance for n, d in found)
    return hit, f"toothed outlines (teeth, tip diameter) {sorted({(n, round(d, 2)) for n, d in found})[:8]}"


# every closed outline of sections across x, y and z, as (lobes over its mid radius, outer diameter)
def toothed_rings(m: trimesh.Trimesh) -> list[tuple[int, float]]:
    lo, hi = m.bounds
    found = []
    for axis in range(3):
        normal = np.eye(3)[axis]
        for f in LEVELS:
            segments = trimesh.intersections.mesh_plane(m, normal, lo + (hi - lo) * f)
            found += [lobes(np.delete(loop, axis, 1)) for loop in loops(segments)]
    return [r for r in found if r[0] > 0]


def loops(segments: Array) -> list[Array]:
    keys = [tuple(k) for k in np.round(segments.reshape(-1, 3), 5)]
    parent = list(range(len(keys)))
    first: dict[tuple[float, ...], int] = {}

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, k in enumerate(keys):
        parent[root(i)] = root(first.setdefault(k, i))
        if i % 2:
            parent[root(i)] = root(i - 1)
    groups: dict[int, list[int]] = {}
    for i in range(len(keys)):
        groups.setdefault(root(i), []).append(i)
    points = segments.reshape(-1, 3)
    return [np.unique(points[idx], axis=0) for idx in groups.values() if len(idx) >= 6]


def lobes(p: Array) -> tuple[int, float]:
    d = p - p.mean(axis=0)
    r = np.hypot(d[:, 0], d[:, 1])
    if r.max() - r.min() < 1e-3 * r.max():
        return 0, 2 * float(r.max())
    high = (r > (r.max() + r.min()) / 2)[np.argsort(np.arctan2(d[:, 1], d[:, 0]))]
    return int(np.sum(high & ~np.roll(high, 1))), 2 * float(r.max())
