import math
from dataclasses import dataclass

import numpy as np

from partwright_geometry.mesh_sections import Points

Pt = tuple[float, float]


@dataclass(frozen=True)
class Circle2:
    x: float
    y: float
    r: float
    rms: float


@dataclass(frozen=True)
class Polar:
    x: float
    y: float
    diameter: float
    start_angle: float


@dataclass(frozen=True)
class Grid:
    x: float
    y: float
    nx: int
    ny: int
    sx: float
    sy: float


def fit_circle(p: Points) -> Circle2:
    a = np.c_[2 * p, np.ones(len(p))]
    (cx, cy, c), *_ = np.linalg.lstsq(a, (p**2).sum(axis=1), rcond=None)
    r = math.sqrt(c + cx * cx + cy * cy)
    for _ in range(20):
        d = p - (cx, cy)
        dist = np.hypot(d[:, 0], d[:, 1])
        jac = np.c_[-d / dist[:, None], -np.ones(len(p))]
        step, *_ = np.linalg.lstsq(jac, -(dist - r), rcond=None)
        cx, cy, r = cx + step[0], cy + step[1], r + step[2]
        if np.abs(step).max() < 1e-10:
            break
    res = np.hypot(p[:, 0] - cx, p[:, 1] - cy) - r
    return Circle2(float(cx), float(cy), float(r), float(np.sqrt(np.mean(res**2))))


def robust_circle(p: Points) -> Circle2:
    c = fit_circle(p)
    for _ in range(3):
        res = np.abs(np.hypot(p[:, 0] - c.x, p[:, 1] - c.y) - c.r)
        keep = res <= 3 * 1.4826 * np.median(res) + 1e-9
        if keep.all() or keep.sum() < 8:
            break
        p = p[keep]
        c = fit_circle(p)
    return c


def simplify(loop: Points, tol: float) -> list[Pt]:
    far = int(np.argmax(np.hypot(*(loop - loop[0]).T)))
    halves = (loop[: far + 1], np.vstack([loop[far:], loop[:1]]))
    kept = [i for h in halves for i in _dp(h, tol)[:-1]]
    return [(float(x), float(y)) for x, y in kept]


def _dp(p: Points, tol: float) -> list[Points]:
    keep = [0, len(p) - 1]
    stack = [(0, len(p) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        seg = p[j] - p[i]
        rel = p[i + 1 : j] - p[i]
        n = np.hypot(*seg)
        dist = np.abs(seg[0] * rel[:, 1] - seg[1] * rel[:, 0]) / n if n > 0 else np.hypot(*rel.T)
        k = int(np.argmax(dist))
        if dist[k] > tol:
            keep.append(i + 1 + k)
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return [p[i] for i in sorted(keep)]


def polar(centres: Points, tol: float) -> Polar | None:
    n = len(centres)
    if n < 3:
        return None
    c = fit_circle(centres)
    step = 2 * math.pi / n
    angles = np.arctan2(centres[:, 1] - c.y, centres[:, 0] - c.x)
    a0 = math.atan2(np.sin(n * angles).mean(), np.cos(n * angles).mean()) / n % step
    drift = np.abs((angles - a0 + step / 2) % step - step / 2) * c.r
    slots = np.round((angles - a0) / step).astype(int) % n
    if c.rms > tol or drift.max() > tol or len(set(slots.tolist())) != n:
        return None
    return Polar(c.x, c.y, 2 * c.r, round(math.degrees(a0), 6) % (360 / n))


def grid(centres: Points, tol: float) -> Grid | None:
    xs, ys = _levels(centres[:, 0], tol), _levels(centres[:, 1], tol)
    if len(xs) * len(ys) != len(centres) or len(centres) < 2:
        return None
    sx, sy = _spacing(xs, tol), _spacing(ys, tol)
    if sx is None or sy is None:
        return None
    g = Grid(float(np.mean(xs)), float(np.mean(ys)), len(xs), len(ys), sx, sy)
    expected = np.array([(g.x + (i - (g.nx - 1) / 2) * sx, g.y + (j - (g.ny - 1) / 2) * sy) for i in range(g.nx) for j in range(g.ny)])
    worst = max(float(np.hypot(*(expected - p).T).min()) for p in centres)
    return g if worst <= tol else None


def _levels(values: Points, tol: float) -> list[float]:
    v = np.sort(values)
    groups = np.split(v, np.where(np.diff(v) > tol)[0] + 1)
    return [float(g.mean()) for g in groups]


def _spacing(levels: list[float], tol: float) -> float | None:
    if len(levels) == 1:
        return 0.0
    gaps = np.diff(levels)
    return float(gaps.mean()) if np.ptp(gaps) <= tol else None
