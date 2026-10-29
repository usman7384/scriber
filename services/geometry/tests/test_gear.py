import math
from pathlib import Path
from typing import Any

import pytest
from build123d import Align, Cylinder, GeomType, Shape, import_step

from partwright_geometry import LocalGeometry, PartMetrics
from partwright_ir import Design, validate

M, Z1, Z2, WIDTH = 2.0, 20, 30, 10.0
MODULE = {"name": "m", "value": M, "unit": "mm"}


def inv(a: float) -> float:
    return math.tan(a) - a


def gear(pid: str, teeth: int, **over: Any) -> dict[str, Any]:
    feature = {"kind": "spur_gear", "id": pid, "name": pid, "module": "m", "teeth": teeth, "face_width": WIDTH, "bore": 8} | over
    return {"id": pid, "name": pid.title(), "sketches": [], "features": [feature]}


def pair(angle: float, backlash: float) -> Design:
    params = [MODULE, {"name": "backlash", "value": backlash, "unit": "mm"}]
    connectors = [{"id": "pinion_axis", "part": "pinion", "origin": ["m * (20 + 30) / 2", 0, 0]}, {"id": "wheel_axis", "part": "wheel"}]
    joint = {"id": "mesh", "parent": "pinion_axis", "child": "wheel_axis", "kind": "revolute", "angle": angle}
    parts = [gear("pinion", Z1, backlash="backlash"), gear("wheel", Z2, backlash="backlash")]
    assembly = {"connectors": connectors, "joints": [joint]}
    return Design.model_validate({"title": "Pair", "params": params, "parts": parts, "assembly": assembly})


def tooth_widths(solid: Shape[Any], radius: float) -> list[float]:
    surface = Cylinder(radius, WIDTH, align=(Align.CENTER, Align.CENTER, Align.MIN)).faces().filter_by(GeomType.CYLINDER)[0]
    band = solid & surface
    assert band is not None
    return [f.area / WIDTH for f in band.faces()]


@pytest.fixture(scope="module")
def pinion(geometry: LocalGeometry, tmp_path_factory: pytest.TempPathFactory) -> tuple[Shape[Any], PartMetrics]:
    d = Design.model_validate({"title": "Pinion", "params": [MODULE], "parts": [gear("pinion", Z1, hub_diameter=20, hub_length=5)]})
    assert validate(d) == []
    art = geometry.build(d, tmp_path_factory.mktemp("pinion"))
    return import_step(art.files["step"]).solids()[0], art.parts[0]


def test_tooth_count_pitch_and_tip_diameters(pinion: tuple[Shape[Any], PartMetrics]) -> None:
    solid, metrics = pinion
    at_pitch = tooth_widths(solid, M * Z1 / 2)
    assert at_pitch == pytest.approx([math.pi * M / 2] * Z1, abs=1e-6)
    assert 2 * max(math.hypot(v.X, v.Y) for v in solid.vertices()) == pytest.approx(M * (Z1 + 2), abs=1e-6)
    assert metrics.bbox_size[2] == pytest.approx(WIDTH + 5, abs=1e-6)
    assert [h.diameter for h in metrics.holes] == pytest.approx([8])


@pytest.mark.parametrize("radius", [19.1, 20.6, 21.6])
def test_flanks_are_involutes(pinion: tuple[Shape[Any], PartMetrics], radius: float) -> None:
    pa = math.radians(20)
    base = M * Z1 / 2 * math.cos(pa)
    expected = 2 * radius * (math.pi / 2 / Z1 + inv(pa) - inv(math.acos(base / radius)))
    assert tooth_widths(pinion[0], radius) == pytest.approx([expected] * Z1, abs=1e-3)


def test_pair_at_the_standard_centre_distance_meshes_with_the_set_backlash(geometry: LocalGeometry, tmp_path: Path) -> None:
    centred = 180 / Z2
    art = geometry.build(pair(centred, 0.2), tmp_path / "centred")
    assert art.assembly is not None and art.assembly.overlaps() == []
    assert art.assembly.mates[0].gap == pytest.approx(0.2 / 2 * math.cos(math.radians(20)), abs=1e-5)
    turned = geometry.build(pair(centred + 0.4, 0.2), tmp_path / "turned")
    assert turned.assembly is not None and turned.assembly.overlaps()[0].volume > 1
    tight = geometry.build(pair(centred, 0.0), tmp_path / "tight")
    assert tight.assembly is not None and tight.assembly.overlaps() == []
    assert tight.assembly.mates[0].gap == pytest.approx(0, abs=1e-6)
