from pathlib import Path

import numpy as np
import trimesh
from numpy.typing import NDArray
from scipy.spatial import cKDTree

SAMPLES = 20000
CANDIDATES = 16
CHUNK = 4096

Array = NDArray[np.float64]


def hausdorff(a: Path, b: Path) -> float:
    ma, mb = trimesh.load_mesh(a, force="mesh"), trimesh.load_mesh(b, force="mesh")
    return max(one_sided(ma, mb), one_sided(mb, ma))


def one_sided(src: trimesh.Trimesh, dst: trimesh.Trimesh, seed: int = 0) -> float:
    points = np.vstack([src.vertices, trimesh.sample.sample_surface(src, SAMPLES, seed=seed)[0]])
    bound = distance_bounds(points, dst)
    worst = 0.0
    # bounds are never below the true distance, so once the next bound is under the worst exact distance the max is settled
    for i in np.argsort(-bound):
        if bound[i] <= worst:
            break
        worst = max(worst, _exact(points[i], dst.triangles))
    return worst


def distance_bounds(points: Array, mesh: trimesh.Trimesh) -> Array:
    v, f = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, max_edge=float(np.linalg.norm(mesh.extents)) / 50, max_iter=20)
    triangles = v[f]
    tree = cKDTree(triangles.mean(axis=1))
    return np.concatenate([_nearest(points[i : i + CHUNK], triangles, tree) for i in range(0, len(points), CHUNK)])


def _nearest(points: Array, triangles: Array, tree: cKDTree) -> Array:
    k = min(CANDIDATES, len(triangles))
    _, near = tree.query(points, k=k)
    p = np.repeat(points, k, axis=0)
    gaps: Array = np.linalg.norm(trimesh.triangles.closest_point(triangles[near.ravel()], p) - p, axis=1)
    return gaps.reshape(len(points), k).min(axis=1)


def _exact(point: Array, triangles: Array) -> float:
    p = np.repeat(point[None], len(triangles), axis=0)
    return float(np.linalg.norm(trimesh.triangles.closest_point(triangles, p) - p, axis=1).min())
