import math
from pathlib import Path
from typing import Any

import pytest
from build123d import Align, Cylinder, GeomType, Shape, import_step

from partwright_geometry import LocalGeometry, PartMetrics
from partwright_ir import Design, Rule, RuleSet, validate

M, Z1, Z2, WIDTH = 2.0, 20, 30, 10.0
MODULE = {"name": "m", "value": M, "unit": "mm"}


def inv(a: float) -> float:
    return math.tan(a) - a


def gear(pid: str, teeth: int, **over: Any) -> dict[str, Any]:
    feature = {"kind": "spur_gear", "id": pid, "name": pid, "module": "m", "teeth": teeth, "face_width": WIDTH, "bore": 8} | over
    return {"id": pid, "name": pid.title(), "sketches": [], "features": [feature]}


def pair(angle: float, backlash: float, z1: int = Z1, z2: int = Z2) -> Design:
    params = [MODULE, {"name": "backlash", "value": backlash, "unit": "mm"}]
    origin = [f"m * ({z1} + {z2}) / 2", 0, 0]
    connectors = [{"id": "pinion_axis", "part": "pinion", "origin": origin}, {"id": "wheel_axis", "part": "wheel"}]
    joint = {"id": "mesh", "parent": "pinion_axis", "child": "wheel_axis", "kind": "revolute", "angle": angle}
    parts = [gear("pinion", z1, backlash="backlash"), gear("wheel", z2, backlash="backlash")]
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
    assert art.assembly is not None and art.assembly.overlaps() == [] and art.assembly.broken_mates() == [] and art.ok
    assert art.assembly.mates[0].gap == pytest.approx(0.2 / 2 * math.cos(math.radians(20)), abs=1e-5)
    turned = geometry.build(pair(centred + 0.4, 0.2), tmp_path / "turned")
    assert turned.assembly is not None and turned.assembly.overlaps()[0].volume > 1
    tight = geometry.build(pair(centred, 0.0), tmp_path / "tight")
    assert tight.assembly is not None and tight.assembly.overlaps() == [] and tight.ok
    assert tight.assembly.mates[0].gap == pytest.approx(0, abs=1e-5)


# flank splines of these pairs overlap by ~1e-5 mm3 at zero backlash (16/24 leaves a 1.4e-6 mm gap instead)
@pytest.mark.parametrize(("z1", "z2"), [(22, 33), (25, 50), (16, 24)])
def test_meshes_pass_at_any_backlash_and_an_overlapping_mesh_fails(geometry: LocalGeometry, tmp_path: Path, z1: int, z2: int) -> None:
    centred = 180 / z2 if z2 % 2 == 0 else 0.0
    for backlash in (0.0, 0.1):
        art = geometry.build(pair(centred, backlash, z1, z2), tmp_path / f"b{backlash}")
        assert art.ok, art.findings
    turned = geometry.build(pair(centred + 0.4, 0.0, z1, z2), tmp_path / "turned")
    assert {f.rule_id for f in turned.findings} == {"ASM-INTERFERENCE"}


def test_wall_check_on_a_40_tooth_gear_takes_seconds(geometry: LocalGeometry, tmp_path: Path) -> None:
    d = Design.model_validate({"title": "Wheel", "params": [MODULE], "parts": [gear("wheel", 40)]})
    plain = geometry.build(d, tmp_path / "plain")
    wall = Rule(id="min-wall", kind="min_wall_thickness", value=0.8, unit="mm")
    checked = geometry.build(d, tmp_path / "checked", rules=RuleSet(rules=[wall]))
    assert checked.ok and checked.elapsed_ms - plain.elapsed_ms < 5000
