from partwright_agent.grounding import grounded
from partwright_agent.requirements import Requirement


def test_drops_requirements_copied_from_elsewhere() -> None:
    text = "make the plate 100 mm long and use 6.6 mm holes"
    reqs = [
        Requirement(kind="extent", description="length 100", value=100),
        Requirement(kind="extent", description="width 40", value=40),
        Requirement(kind="holes", description="six holes 6.6", count=6, diameter_min=6.5, diameter_max=6.7),
        Requirement(kind="holes", description="holes 6.6", diameter_min=6.5, diameter_max=6.7),
        Requirement(kind="wall", description="wall 2", value=2),
    ]
    assert [r.description for r in grounded(reqs, text)] == ["length 100", "holes 6.6"]


def test_keeps_metric_hole_ranges_and_number_words() -> None:
    reqs = [Requirement(kind="holes", description="four M6", count=4, diameter_min=6.4, diameter_max=7.0)]
    assert grounded(reqs, "plate with four M6 holes") == reqs
    assert grounded(reqs, "plate with 4x M6 holes") == reqs
