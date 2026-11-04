import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from scriber_geometry import BuildError, LocalGeometry
from scriber_ir import Design, Rule, RuleSet, validate

R, L = 10.0, 60.0
WALL = RuleSet(rules=[Rule(id="min-wall", kind="min_wall_thickness", value=0.8, unit="mm")])


def shaft(*features: dict[str, Any], diameter: float = 2 * R) -> Design:
    part = {
        "id": "p",
        "name": "Shaft",
        "sketches": [{"id": "c", "entities": [{"kind": "circle", "diameter": diameter}]}],
        "features": [{"kind": "extrude", "id": "shaft", "name": "Shaft", "sketch": "c", "distance": L}, *features],
    }
    return Design.model_validate({"title": "Shaft", "params": [], "parts": [part]})


def hub(*features: dict[str, Any], outside: float = 40) -> Design:
    centre = {"kind": "points", "points": [[0, 0]]}
    bore = {"kind": "hole", "id": "bore", "name": "Bore", "plane": {"ref": "XY"}, "at": centre, "diameter": 2 * R}
    part = {
        "id": "p",
        "name": "Hub",
        "sketches": [{"id": "c", "entities": [{"kind": "circle", "diameter": outside}]}],
        "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "c", "distance": 30}, bore, *features],
    }
    return Design.model_validate({"title": "Hub", "params": [], "parts": [part]})


def integral(f: Callable[[float], float], a: float, b: float, n: int = 20000) -> float:
    h = (b - a) / n
    return h / 3 * sum((1 if i in (0, n) else 4 if i % 2 else 2) * f(a + i * h) for i in range(n + 1))


def test_shaft_keyway_takes_din_6885_size_and_removes_the_pocket(geometry: LocalGeometry) -> None:
    key = {"kind": "keyway", "id": "key", "name": "Key", "of": "shaft", "position": 10, "length": 25}
    d = shaft(key)
    assert validate(d) == []
    (part,) = geometry.measure(d)
    b, t1, length = 6.0, 3.5, 25.0

    def removed(y: float) -> float:
        return (length - b + 2 * math.sqrt(max(b * b / 4 - y * y, 0))) * (math.sqrt(R * R - y * y) - (R - t1))

    # OCCT integrates the cylinder-cylinder intersection faces to about 1e-6 of the part volume
    assert part.volume == pytest.approx(math.pi * R * R * L - integral(removed, -b / 2, b / 2), rel=1e-6)
    assert part.bbox_size == pytest.approx((2 * R, 2 * R, L))


def test_bore_keyway_runs_through_the_hub(geometry: LocalGeometry) -> None:
    (part,) = geometry.measure(hub({"kind": "keyway", "id": "key", "name": "Key", "of": "bore", "on": "bore"}))
    b, t2 = 6.0, 2.8
    area = b * (R + t2) - (b / 2 * math.sqrt(R * R - b * b / 4) + R * R * math.asin(b / 2 / R))
    assert math.pi * (20**2 - R**2) * 30 - part.volume == pytest.approx(area * 30, rel=1e-9)


def test_circlip_groove_on_a_shaft_and_o_ring_groove_in_a_bore(geometry: LocalGeometry) -> None:
    circlip = {"kind": "groove", "id": "circlip", "name": "Circlip", "of": "shaft", "position": 50, "width": 1.1, "depth": 0.6}
    (part,) = geometry.measure(shaft(circlip))
    assert math.pi * R * R * L - part.volume == pytest.approx(math.pi * (R**2 - (R - 0.6) ** 2) * 1.1, rel=1e-9)
    oring = {"kind": "groove", "id": "oring", "name": "O-ring", "of": "bore", "on": "bore", "position": 10, "width": 2.4, "depth": 1.8}
    (bored,) = geometry.measure(hub(oring))
    assert math.pi * (20**2 - R**2) * 30 - bored.volume == pytest.approx(math.pi * ((R + 1.8) ** 2 - R**2) * 2.4, rel=1e-9)


def test_groove_past_the_shaft_end_is_an_error(geometry: LocalGeometry) -> None:
    late = {"kind": "groove", "id": "late", "name": "Late", "of": "shaft", "position": 59.5, "width": 1, "depth": 0.5}
    with pytest.raises(BuildError, match=r"groove late: no shaft surface runs from 59\.5"):
        geometry.measure(shaft(late))


@pytest.mark.parametrize("diameter", [8.0, 12.0, 16.0, 18.0])
def test_small_keyed_shafts_have_no_thin_wall_at_the_keyway_edge(geometry: LocalGeometry, tmp_path: Path, diameter: float) -> None:
    key = {"kind": "keyway", "id": "key", "name": "Key", "of": "shaft", "position": 10, "length": 25}
    art = geometry.build(shaft(key, diameter=diameter), tmp_path, rules=WALL)
    assert art.ok, art.findings


def test_a_keyway_floor_close_to_the_outside_is_a_thin_wall(geometry: LocalGeometry, tmp_path: Path) -> None:
    key = {"kind": "keyway", "id": "key", "name": "Key", "of": "bore", "on": "bore", "width": 6, "depth": 1.6}
    art = geometry.build(hub(key, outside=24), tmp_path, rules=WALL)
    (thin,) = art.findings
    assert thin.measured is not None and thin.measured < 0.8 and not art.ok


@pytest.mark.parametrize("angle", [0.0, 90.0])
def test_a_keyed_bore_is_measured_as_a_hole(geometry: LocalGeometry, tmp_path: Path, angle: float) -> None:
    key = {"kind": "keyway", "id": "key", "name": "Key", "of": "bore", "on": "bore", "angle": angle}
    smallest = RuleSet(rules=[Rule(id="min-hole", kind="min_hole_diameter", value=25, unit="mm")])
    art = geometry.build(hub(key), tmp_path, rules=smallest)
    (bore,) = art.parts[0].holes
    assert (bore.diameter, bore.length) == pytest.approx((2 * R, 30)) and bore.center == pytest.approx((0, 0, 15))
    assert [f.measured for f in art.findings] == pytest.approx([2 * R])
