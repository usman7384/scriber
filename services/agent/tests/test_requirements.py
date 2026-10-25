from partwright_agent import Requirement, check
from partwright_geometry import Artifact, HoleInfo, PartMetrics


def artifact(holes: list[HoleInfo], bbox_min: tuple[float, float, float], size: tuple[float, float, float]) -> Artifact:
    part = PartMetrics(id="p", name="P", volume=1, bbox_min=bbox_min, bbox_size=size, solids=1, faces=4, valid=True, holes=holes)
    return Artifact(design_hash="x", files={}, parts=[part], findings=[], elapsed_ms=1)


def test_extent_wall_and_hole_checks() -> None:
    tube = artifact([HoleInfo(diameter=20, axis=(0, 0, 1), center=(0, 0, 25), length=50)], (-12, -12, 0), (24, 24, 50))
    reqs = [
        Requirement(kind="extent", description="height", value=50),
        Requirement(kind="wall", description="wall", value=2, tolerance=0.05),
        Requirement(kind="holes", description="one bore", count=1),
        Requirement(kind="holes", description="M6", count=1, diameter_min=6.4, diameter_max=7),
    ]
    assert [c.passed for c in check(reqs, tube)] == [True, True, True, False]


def test_hole_spacing() -> None:
    plate = artifact([HoleInfo(diameter=5, axis=(0, 0, 1), center=(x, 0, 0), length=5) for x in (0, 20, 40)], (0, 0, 0), (50, 10, 5))
    reqs = [Requirement(kind="hole_spacing", description="pitch", value=20), Requirement(kind="hole_spacing", description="x", value=25)]
    ok, bad = check(reqs, plate)
    assert ok.passed and not bad.passed
