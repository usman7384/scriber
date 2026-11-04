import math
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scriber_geometry import Artifact, HoleInfo


class Requirement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["extent", "max_extent", "holes", "min_holes", "hole_spacing", "wall", "counterbores", "crossing_holes", "hole_axes"]
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
    return [_check(r, artifact) for r in reqs]


def _check(r: Requirement, artifact: Artifact) -> CheckResult:
    size = overall_size(artifact)
    holes = _holes(r, artifact)
    if r.kind == "extent":
        return _result(r, _near(size, r), "bounding box " + " x ".join(f"{s:.2f}" for s in size) + " mm")
    if r.kind == "hole_spacing":
        gaps = sorted({round(_dist(a.center, b.center), 2) for i, a in enumerate(holes) for b in holes[i + 1 :]})
        return _result(r, _near(gaps, r), f"hole centre distances {gaps[:12]}")
    if r.kind == "wall":
        walls = sorted({round((max(size[:2]) - h.diameter) / 2, 3) for h in holes})
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
    passed = bool(holes) if r.count is None else r.count == len(holes)
    return _result(r, passed, f"{len(holes)} matching holes; all hole diameters {all_d}")


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


def _holes(r: Requirement, artifact: Artifact) -> list[HoleInfo]:
    lo, hi = r.diameter_min or 0.0, r.diameter_max or float("inf")
    return [h for p in artifact.parts for h in p.holes if lo - 1e-6 <= h.diameter <= hi + 1e-6]


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
