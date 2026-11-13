import math
from collections.abc import Sequence
from itertools import combinations, permutations
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scriber_geometry import Artifact, HoleInfo

Vec = tuple[float, float, float]


class Requirement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal[
        "extent",
        "max_extent",
        "holes",
        "min_holes",
        "hole_spacing",
        "pitch_circle",
        "wall",
        "counterbores",
        "crossing_holes",
        "hole_axes",
        "threads",
    ]
    description: str
    value: float | None = Field(default=None, description="extent: overall size; hole_spacing: centre distance; wall: wall thickness (mm)")
    tolerance: float = 0.1
    count: int | None = Field(default=None, description="holes: number of holes")
    diameter_min: float | None = None
    diameter_max: float | None = None
    axis: Literal["x", "y", "z"] | None = None


class RequirementList(BaseModel):
    requirements: list[Requirement]


class CheckResult(BaseModel):
    requirement: Requirement
    passed: bool
    actual: str


def check(reqs: list[Requirement], artifact: Artifact) -> list[CheckResult]:
    results = [_check(r, artifact) for r in reqs]
    extents = [i for i, r in enumerate(reqs) if r.kind == "extent"]
    if len(extents) > 1:
        # stated sizes are different axes of the part: 80 x 60 x 10 must not all pass on one 80 mm side
        fits = _distinct_axes([reqs[i] for i in extents], overall_size(artifact))
        for i, ok in zip(extents, fits, strict=True):
            results[i] = results[i].model_copy(update={"passed": ok})
    return results


def _distinct_axes(reqs: list[Requirement], size: tuple[float, float, float]) -> list[bool]:
    slots: list[int | None] = [0, 1, 2, *[None] * max(0, len(reqs) - 3)]
    best = max(
        (
            tuple(a is not None and r.value is not None and abs(size[a] - r.value) <= r.tolerance for r, a in zip(reqs, p, strict=True))
            for p in permutations(slots, len(reqs))
        ),
        key=sum,
    )
    return list(best)


def _check(r: Requirement, artifact: Artifact) -> CheckResult:
    size = overall_size(artifact)
    holes = _holes(r, artifact)
    if r.kind == "threads":
        return _threads(r, artifact)
    if r.kind == "extent":
        return _result(r, _near(size, r), "bounding box " + " x ".join(f"{s:.2f}" for s in size) + " mm")
    if r.kind == "hole_spacing":
        gaps = _spacings(holes)
        return _result(r, _near(gaps, r), f"spacings to neighbouring holes {gaps[:12]}")
    if r.kind == "pitch_circle":
        circles = _pitch_circles(holes)
        return _result(r, _near(circles, r), f"hole circles (diameter) {circles[:8]}")
    if r.kind == "wall":
        walls = sorted({round((_across(size, h) - h.diameter) / 2, 3) for h in holes})
        return _result(r, _near(walls, r), f"wall from outer size and holes {walls}")
    if r.kind == "max_extent":
        i = "xyz".index(r.axis or "x")
        return _result(r, r.value is not None and size[i] <= r.value + r.tolerance, f"{(r.axis or 'x').upper()} extent {size[i]:.2f} mm")
    if r.kind in ("counterbores", "crossing_holes", "hole_axes"):
        found = {"counterbores": _stepped, "crossing_holes": _crossing, "hole_axes": _axes}[r.kind](holes)
        return _result(r, found >= (r.count or 1), f"{found} found")
    all_d = sorted(round(h.diameter, 2) for p in artifact.parts for h in p.holes)
    if r.kind == "min_holes":
        return _result(r, len(holes) >= (r.count or 1), f"{len(holes)} holes; diameters {all_d[:16]}")
    # an assembly's parts each carry their own pattern: "4x M6" is met by one part with four, not only by four in all
    per_part = [len(_holes(r, artifact, p.id)) for p in artifact.parts]
    passed = bool(holes) if r.count is None else r.count == len(holes) or r.count in per_part
    return _result(r, passed, f"{len(holes)} matching holes; all hole diameters {all_d}")


def _spacings(holes: list[HoleInfo]) -> list[float]:
    # a spacing is to the nearest hole or along a row or column (chain or baseline dimensions), never across a diagonal
    gaps: set[float] = set()
    for a in holes:
        others = [b for b in holes if b is not a and not _coaxial(a, b)]
        if not others:
            continue
        gaps.add(round(min(_dist(a.center, b.center) for b in others), 2))
        for k in range(3):
            gaps |= {round(abs(b.center[k] - a.center[k]), 2) for b in others if _only_along(a, b, k)}
    return sorted(gaps)


def _only_along(a: HoleInfo, b: HoleInfo, k: int) -> bool:
    return abs(b.center[k] - a.center[k]) > 1e-3 and all(abs(b.center[j] - a.center[j]) < 1e-3 for j in range(3) if j != k)


def _threads(r: Requirement, artifact: Artifact) -> CheckResult:
    def fits(major: float) -> bool:
        return (r.diameter_min is None or major >= r.diameter_min - 1e-6) and (r.diameter_max is None or major <= r.diameter_max + 1e-6)

    per_part = [sum(fits(t.major) for t in p.threads) for p in artifact.parts]
    found = sum(per_part)
    passed = found > 0 if r.count is None else r.count == found or r.count in per_part
    names = sorted({t.designation for p in artifact.parts for t in p.threads})
    return _result(r, passed, f"{found} matching threads; all threads {names}")


def _stepped(holes: list[HoleInfo]) -> int:
    return sum(1 for i, a in enumerate(holes) for b in holes[i + 1 :] if _coaxial(a, b) and abs(a.diameter - b.diameter) > 1e-3)


def _crossing(holes: list[HoleInfo]) -> int:
    return sum(1 for i, a in enumerate(holes) for b in holes[i + 1 :] if _cross(a, b) and _line_gap(a, b) < (a.diameter + b.diameter) / 2)


def _axes(holes: list[HoleInfo]) -> int:
    return len({max(range(3), key=lambda k: abs(h.axis[k])) for h in holes})


def _coaxial(a: HoleInfo, b: HoleInfo) -> bool:
    if _cross(a, b):
        return False
    offset = [b.center[k] - a.center[k] for k in range(3)]
    return _norm(_crossp(offset, a.axis)) < 1e-3


def _cross(a: HoleInfo, b: HoleInfo) -> bool:
    return _norm(_crossp(a.axis, b.axis)) > 1e-3


def _line_gap(a: HoleInfo, b: HoleInfo) -> float:
    n = _crossp(a.axis, b.axis)
    offset = [b.center[k] - a.center[k] for k in range(3)]
    return abs(sum(offset[k] * n[k] for k in range(3))) / _norm(n)


def _crossp(u: Sequence[float], v: Sequence[float]) -> tuple[float, float, float]:
    return (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])


def _norm(v: Sequence[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _holes(r: Requirement, artifact: Artifact, part: str | None = None) -> list[HoleInfo]:
    lo, hi = r.diameter_min or 0.0, r.diameter_max or float("inf")
    return [h for p in artifact.parts if part in (None, p.id) for h in p.holes if lo - 1e-6 <= h.diameter <= hi + 1e-6]


def _across(size: tuple[float, float, float], h: HoleInfo) -> float:
    # the outer size across a bore is measured in the two axes the bore does not run along
    along = max(range(3), key=lambda i: abs(h.axis[i]))
    return max(s for i, s in enumerate(size) if i != along)


def _pitch_circles(holes: list[HoleInfo]) -> list[float]:
    # every circle through three hole centres that at least three holes lie on; holes from other patterns do not spoil it
    found: set[float] = set()
    centres = [h.center for h in holes[:24]]
    for a, b, c in combinations(centres, 3):
        circle = _circumcircle(a, b, c)
        if circle and sum(abs(math.dist(circle[0], p) - circle[1]) < 0.05 for p in centres) >= 3:
            found.add(round(2 * circle[1], 2))
    return sorted(found)


def _circumcircle(a: Vec, b: Vec, c: Vec) -> tuple[Vec, float] | None:
    ab, ac = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
    n = _crossp(ab, ac)
    nn = sum(v * v for v in n)
    if nn < 1e-9:
        return None
    ab2, ac2 = sum(v * v for v in ab), sum(v * v for v in ac)
    # centre = a + (|ac|^2 (n x ab) + |ab|^2 (ac x n)) / (2 |n|^2)
    u = [ac2 * x + ab2 * y for x, y in zip(_crossp(n, ab), _crossp(ac, n), strict=True)]
    centre = (a[0] + u[0] / (2 * nn), a[1] + u[1] / (2 * nn), a[2] + u[2] / (2 * nn))
    return centre, math.dist(centre, a)


def _near(values: Sequence[float], r: Requirement) -> bool:
    return r.value is not None and any(abs(v - r.value) <= r.tolerance for v in values)


def _dist(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.dist(a, b)


def _result(r: Requirement, passed: bool, actual: str) -> CheckResult:
    return CheckResult(requirement=r, passed=passed, actual=actual)


def overall_size(artifact: Artifact) -> tuple[float, float, float]:
    lo = [min(p.bbox_min[i] for p in artifact.parts) for i in range(3)]
    hi = [max(p.bbox_min[i] + p.bbox_size[i] for p in artifact.parts) for i in range(3)]
    return (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
