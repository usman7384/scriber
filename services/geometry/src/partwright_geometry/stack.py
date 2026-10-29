from dataclasses import dataclass

import numpy as np
import trimesh

from partwright_geometry.fits import Circle2, Pt, fit_circle, robust_circle, simplify
from partwright_geometry.sections import Points, depths, section_loops, signed_area

FLAT = 0.95
LEVEL_GAP = 0.5
BIN = 0.25
DENSE = 0.005
MIN_LEVEL_SHARE = 0.01
WALL = 0.05


@dataclass(frozen=True)
class Profile:
    circle: Circle2 | None
    polygon: tuple[Pt, ...]
    area: float
    centroid: Pt


@dataclass(frozen=True)
class Body:
    lo: int
    hi: int
    outlines: tuple[Profile, ...]


@dataclass(frozen=True)
class Opening:
    lo: int
    hi: int
    profile: Profile


@dataclass(frozen=True)
class Stack:
    levels: tuple[float, ...]
    bodies: tuple[Body, ...]
    openings: tuple[Opening, ...]
    noise: float


def analyse(mesh: trimesh.Trimesh) -> Stack:
    if not mesh.is_watertight:
        raise ValueError("mesh is not watertight; close it before reconstruction")
    levels, noise = _levels(mesh)
    slabs = [_slab(mesh, levels[i], levels[i + 1], noise) for i in range(len(levels) - 1)]
    tol = 0.1 + 3 * noise
    bodies: list[Body] = []
    open_: list[Opening] = []
    for i, (outers, inners) in enumerate(slabs):
        last = bodies[-1] if bodies else None
        if last and last.hi == i and _same_all(last.outlines, outers, tol):
            bodies[-1] = Body(last.lo, i + 1, last.outlines)
        elif outers:
            bodies.append(Body(i, i + 1, outers))
        for p in inners:
            k = next((k for k, o in enumerate(open_) if o.hi == i and _same(o.profile, p, tol)), None)
            if k is None:
                open_.append(Opening(i, i + 1, p))
            else:
                open_[k] = Opening(open_[k].lo, i + 1, open_[k].profile)
    if not bodies:
        raise ValueError("mesh has no closed sections normal to Z")
    return Stack(tuple(levels), tuple(bodies), tuple(open_), noise)


def _levels(mesh: trimesh.Trimesh) -> tuple[list[float], float]:
    flat = np.abs(mesh.face_normals[:, 2]) > FLAT
    if not flat.any():
        raise ValueError("mesh has no faces normal to Z; only Z-stacked prismatic shapes are supported")
    z, w = mesh.triangles_center[flat, 2], mesh.area_faces[flat]
    bins = np.arange(z.min() - BIN, z.max() + 2 * BIN, BIN)
    # area histogram, not gaps between face heights: stray flat slivers on noisy walls would bridge every gap
    hist, _ = np.histogram(z, bins=bins, weights=w)
    dense = np.flatnonzero(hist >= DENSE * w.sum())
    levels, spread = [], []
    for run in np.split(dense, np.where(np.diff(dense) > 1)[0] + 1):
        near = (z >= bins[run[0]] - BIN) & (z < bins[run[-1] + 1] + BIN)
        if w[near].sum() < MIN_LEVEL_SHARE * w.sum():
            continue
        mid = _weighted_median(z[near], w[near])
        levels.append(mid)
        spread.append(_weighted_median(np.abs(z[near] - mid), w[near]))
    noise = float(1.4826 * np.sqrt(3) * np.median(spread))
    lo, hi, gap = float(mesh.bounds[0, 2]), float(mesh.bounds[1, 2]), LEVEL_GAP + 6 * noise
    edges = [lo] if levels[0] - lo > gap else []
    edges += levels + ([hi] if hi - levels[-1] > gap else [])
    return edges, noise


def _weighted_median(values: Points, weights: Points) -> float:
    order = np.argsort(values)
    return float(values[order][np.searchsorted(np.cumsum(weights[order]), weights.sum() / 2)])


def _slab(mesh: trimesh.Trimesh, lo: float, hi: float, noise: float) -> tuple[tuple[Profile, ...], tuple[Profile, ...]]:
    # noise folds on scanned walls leave tiny closed loops in a section; they are not features
    loops = [p for p in section_loops(mesh, (lo + hi) / 2) if abs(signed_area(p)) > max((10 * noise) ** 2, 0.01)]
    # tessellation vertices lie on the true surface, unlike section points, which sit on chords
    on_wall = np.zeros(len(mesh.vertices), dtype=bool)
    on_wall[mesh.faces[np.abs(mesh.face_normals[:, 2]) < WALL].ravel()] = True
    z = mesh.vertices[:, 2]
    near = mesh.vertices[on_wall & (z >= lo) & (z <= hi), :2]
    profiles = [_profile(loop, near, noise) for loop in loops]
    parity = depths(loops)
    outers = tuple(p for p, d in zip(profiles, parity, strict=True) if d % 2 == 0)
    inners = tuple(p for p, d in zip(profiles, parity, strict=True) if d % 2 == 1)
    return outers, inners


def _profile(loop: Points, near: Points, noise: float) -> Profile:
    area = abs(signed_area(loop))
    centroid = (float(loop[:, 0].mean()), float(loop[:, 1].mean()))
    c = fit_circle(loop)
    if c.rms > 0.01 * c.r + 1.5 * noise + 0.005:
        ccw = loop if signed_area(loop) > 0 else loop[::-1]
        return Profile(None, tuple(simplify(ccw, 0.02 + 3 * noise)), area, centroid)
    pts = near[np.abs(np.hypot(near[:, 0] - c.x, near[:, 1] - c.y) - c.r) < 0.1 * c.r + 4 * noise]
    return Profile(robust_circle(pts if len(pts) >= 8 else loop), (), area, (c.x, c.y))


def _same(a: Profile, b: Profile, tol: float) -> bool:
    if a.circle and b.circle:
        return bool(np.hypot(a.circle.x - b.circle.x, a.circle.y - b.circle.y) <= tol and abs(a.circle.r - b.circle.r) <= tol)
    if a.circle or b.circle:
        return False
    return abs(a.area - b.area) <= 0.02 * a.area and bool(np.hypot(a.centroid[0] - b.centroid[0], a.centroid[1] - b.centroid[1]) <= 0.5)


def _same_all(a: tuple[Profile, ...], b: tuple[Profile, ...], tol: float) -> bool:
    return len(a) == len(b) and all(any(_same(p, q, tol) for q in b) for p in a)
