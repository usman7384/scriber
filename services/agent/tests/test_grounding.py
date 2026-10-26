from partwright_agent.grounding import grounded, measurable
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


THICK = Requirement(kind="extent", description="plate thickness 4", value=4)
WALL = Requirement(kind="wall", description="wall 2", value=2)


def test_stock_thickness_of_a_bent_part_is_not_an_extent() -> None:
    length = Requirement(kind="extent", description="length 120", value=120)
    assert measurable([THICK, length], "L-bracket from 4 mm plate, 120 mm long, two holes in each leg") == [length]
    assert measurable([THICK, length], "mounting plate 120 x 80, 4 mm thick") == [THICK, length]


def test_wall_checks_are_kept_only_for_round_parts() -> None:
    assert measurable([WALL], "Open-top box, outside 100 x 60 x 40 mm, 2 mm walls and floor") == []
    assert measurable([WALL], "Hollow cylinder, 50mm height, 2mm wall thickness") == [WALL]
