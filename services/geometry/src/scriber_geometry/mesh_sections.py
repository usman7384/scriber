from collections import defaultdict

import numpy as np
import trimesh
from numpy.typing import NDArray

Points = NDArray[np.float64]


def section_loops(mesh: trimesh.Trimesh, z: float) -> list[Points]:
    v = mesh.vertices
    edges = mesh.edges_unique
    above = v[:, 2] > z
    crossing = above[edges[:, 0]] != above[edges[:, 1]]
    a, b = v[edges[:, 0]], v[edges[:, 1]]
    t = np.divide(z - a[:, 2], b[:, 2] - a[:, 2], out=np.zeros(len(edges)), where=crossing)
    points = (a + (b - a) * t[:, None])[:, :2]
    hit = crossing[mesh.faces_unique_edges]
    cut = hit.sum(axis=1) == 2
    pairs = mesh.faces_unique_edges[cut][hit[cut]].reshape(-1, 2)
    return [points[ids] for ids in _walk(pairs)]


def _walk(pairs: NDArray[np.int64]) -> list[list[int]]:
    links: dict[int, list[int]] = defaultdict(list)
    for i, j in pairs.tolist():
        links[i].append(j)
        links[j].append(i)
    if any(len(n) != 2 for n in links.values()):
        raise ValueError("mesh section is not a set of closed loops; the mesh must be watertight")
    seen: set[int] = set()
    loops = []
    for start in links:
        if start in seen:
            continue
        loop, prev, cur = [start], -1, start
        while True:
            a, b = links[cur]
            prev, cur = cur, b if a == prev else a
            if cur == start:
                break
            loop.append(cur)
        seen.update(loop)
        loops.append(loop)
    return loops


def signed_area(p: Points) -> float:
    x, y = p[:, 0], p[:, 1]
    return float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y)) / 2


def inside(point: Points, poly: Points) -> bool:
    x, y = point
    a, b = poly, np.roll(poly, -1, axis=0)
    straddles = (a[:, 1] > y) != (b[:, 1] > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        cross_x = a[:, 0] + (y - a[:, 1]) * (b[:, 0] - a[:, 0]) / (b[:, 1] - a[:, 1])
    return bool(np.count_nonzero(straddles & (x < cross_x)) % 2)


def depths(loops: list[Points]) -> list[int]:
    return [sum(inside(p[0], q) for j, q in enumerate(loops) if j != i) for i, p in enumerate(loops)]
