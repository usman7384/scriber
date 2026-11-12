from collections.abc import Iterator
from pathlib import Path

import pytest

from scriber_context import DEFAULT_RULES
from scriber_geometry import LocalGeometry
from scriber_ir import Design, apply_params, validate

GEARBOX = Path(__file__).parents[1] / "reference" / "two-stage-gearbox.json"
VARIANTS = [
    {},
    {"module": 2, "pinion_teeth": 20, "wheel_teeth": 60},
    {"face_width": 20},
    {"journal_diameter": 17, "bearing_od": 35, "bearing_width": 10, "shaft_diameter": 22, "clearance_hole": 24, "ratchet_diameter": 44},
]


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=600)
    yield g
    g.close()


@pytest.mark.parametrize("change", VARIANTS, ids=["as-drawn", "module-2-even-teeth", "wide-gears", "bigger-bearings"])
def test_gearbox_assembles_without_clashes(change: dict[str, float], geometry: LocalGeometry, tmp_path: Path) -> None:
    design = apply_params(Design.model_validate_json(GEARBOX.read_text(encoding="utf-8")), change)
    assert validate(design) == []
    artifact = geometry.build(design, tmp_path, DEFAULT_RULES.for_process("casting"))
    assembly = artifact.assembly
    assert assembly is not None
    assert len(artifact.parts) == 18 and all(p.valid for p in artifact.parts)
    assert len(assembly.mates) == 17 and assembly.broken_mates() == [] and assembly.overlaps() == []
    assert [f.message for f in artifact.findings if f.severity == "error"] == []
