from pathlib import Path
from typing import Any

import pytest

from scriber_geometry import LocalGeometry
from scriber_ir import Design


def block(pid: str, size: float, material: str) -> dict[str, Any]:
    return {
        "id": pid,
        "name": pid.title(),
        "material": material,
        "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": size, "height": size}]}],
        "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": size}],
    }


def stack(offset: float = 0, angle: float = 0) -> Design:
    joint = {"id": "cube_on_plate", "parent": "seat", "child": "foot", "offset": offset, "angle": angle}
    return Design.model_validate(
        {
            "title": "Stack",
            "params": [],
            "parts": [block("plate", 40, "steel"), block("cube", 10, "PLA")],
            "assembly": {
                "connectors": [
                    {"id": "seat", "part": "plate", "origin": [10, 0, 40], "z": "+z", "x": "+y"},
                    {"id": "foot", "part": "cube", "origin": [0, 0, 0]},
                ],
                "joints": [joint],
            },
        }
    )


def test_mated_part_is_placed_and_reported(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(stack(angle=90), tmp_path)
    cube = art.parts[1]
    assert art.ok, art.findings
    assert cube.bbox_min == pytest.approx((5, -5, 40), abs=1e-9)
    assert cube.placement is not None and cube.placement[0] == pytest.approx((-1, 0, 0, 10), abs=1e-12)
    assert art.assembly is not None and art.assembly.broken_mates() == [] and art.assembly.overlaps() == []
    assert [(m.joint, m.gap) for m in art.assembly.mates] == [("cube_on_plate", 0.0)]
    plate_g, cube_g = 64000 * 7.85 / 1000, 1000 * 1.24 / 1000
    assert art.assembly.mass_g == pytest.approx(plate_g + cube_g, rel=1e-9)
    total = plate_g + cube_g
    assert art.assembly.center_of_mass == pytest.approx((10 * cube_g / total, 0, (20 * plate_g + 45 * cube_g) / total))


def test_overlapping_and_floating_mates_are_errors(geometry: LocalGeometry, tmp_path: Path) -> None:
    sunk = geometry.build(stack(offset=-2), tmp_path / "sunk")
    assert {f.rule_id for f in sunk.findings} == {"ASM-INTERFERENCE"}
    assert sunk.assembly is not None and sunk.assembly.overlaps()[0].volume == pytest.approx(200)
    assert sunk.assembly.broken_mates() == ["cube_on_plate"]
    floating = geometry.build(stack(offset=1), tmp_path / "floating")
    assert {f.rule_id for f in floating.findings} == {"ASM-MATE"}
    assert floating.findings[0].measured == pytest.approx(1)


def test_step_keeps_product_structure_and_placements(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(stack(angle=30), tmp_path)
    step = art.files["step"].read_text(encoding="utf-8", errors="replace")
    reloaded = geometry.import_step(art.files["step"])
    assert step.count("NEXT_ASSEMBLY_USAGE_OCCURRENCE") == 2
    for built, back in zip(art.parts, reloaded, strict=True):
        assert built.placement is not None and back.placement is not None
        assert [x for r in back.placement for x in r] == pytest.approx([x for r in built.placement for x in r], abs=1e-9)


def test_single_parts_have_no_assembly_report(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(stack().model_copy(update={"assembly": None}), tmp_path)
    assert art.assembly is None
