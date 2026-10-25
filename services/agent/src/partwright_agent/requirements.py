import math
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from partwright_geometry import Artifact, HoleInfo


class Requirement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["extent", "holes", "hole_spacing", "wall"]
    description: str
    value: float | None = Field(default=None, description="extent: overall size; hole_spacing: centre distance; wall: wall thickness (mm)")
    tolerance: float = 0.1
    count: int | None = Field(default=None, description="holes: number of holes")
    diameter_min: float | None = None
    diameter_max: float | None = None


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
    all_d = sorted(round(h.diameter, 2) for p in artifact.parts for h in p.holes)
    passed = bool(holes) if r.count is None else r.count == len(holes)
    return _result(r, passed, f"{len(holes)} matching holes; all hole diameters {all_d}")


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
