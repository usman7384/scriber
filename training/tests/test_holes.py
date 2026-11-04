import random

from scriber_training.holes import Bore, bore, corner_grid
from scriber_training.spec import Draft


def test_holes_are_asked_for_by_size_by_diameter_or_both() -> None:
    bores = [bore(Draft("Plate", "plate"), random.Random(seed), "M6", "simple") for seed in range(200)]
    by_diameter = [b for b in bores if "diameter" in b.spec]
    assert 100 < len(by_diameter) < 180
    assert all(6.4 <= round(b.lo + 0.1, 3) <= 7.0 and round(b.hi - b.lo, 3) == 0.2 for b in by_diameter)
    assert any(b.words.startswith("M6 clearance (") for b in by_diameter)


def test_counterbores_keep_the_fastener() -> None:
    assert bore(Draft("Plate", "plate"), random.Random(0), "M6", "counterbore").spec == {"fastener": "M6", "type": "counterbore"}


def test_count_and_numeric_size_are_separated() -> None:
    assert Bore("6.6 mm", {}, 0, 0).many("4") == "4 x 6.6 mm"
    assert Bore("M6 clearance", {}, 0, 0).many("4") == "4 M6 clearance"
    assert Bore("6.6 mm", {}, 0, 0).many("four") == "four 6.6 mm"


def test_square_patterns_are_one_parameter() -> None:
    for seed in range(40):
        d = Draft("Plate", "plate")
        at, words = corner_grid(d, random.Random(seed), ("plate_length", 60), ("plate_width", 60), 14.5, "hole")
        if words.startswith("on a 31 mm square"):
            assert at["spacing_x"] == at["spacing_y"] == "hole_square"
            assert [c.value for c in d.checks] == [31]
            return
    raise AssertionError("no square wording in 40 seeds")
