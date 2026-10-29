import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals.parity import Evidence, Rig, run_row
from partwright_evals.parity_m5_platform import FREECAD, ROWS
from partwright_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]
THICKER = json.dumps({"suggestions": [{"target": "thickness", "change": {"thickness": 5}, "rationale": "stress at the mount face"}]})


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=300)
    yield g
    g.close()


def run(row: str, geometry: LocalGeometry, out: Path, *answers: str) -> Evidence:
    return run_row(row, ROWS[row], Rig(out, geometry, FakeLLM(list(answers)), load(ROOT / "config.yaml")))


@pytest.mark.parametrize("row", ["AP-6", "AP-9", "DP-19", "WP-10", "WP-11", "WP-12", "CD-7", "CX-12", "CX-14"])
def test_platform_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run(row, geometry, tmp_path)
    assert ev.passed, ev


def test_cd3_scripted_thickness_proposal_brings_stress_under_the_limit(geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run("CD-3", geometry, tmp_path, THICKER)
    assert ev.passed, ev
    assert ev.measured["ratio_before"] == 1.4 and ev.measured["thickness_after"] == 5


@pytest.mark.skipif(any(shutil.which(n) for n in FREECAD), reason="FreeCAD is installed, so the FreeCAD half can be built")
def test_ex5_occt_round_trip_passes_and_the_freecad_half_stays_open(geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run("EX-5", geometry, tmp_path)
    assert ev.measured["documented"] is True and ev.measured["valid"] is True, ev
    assert float(str(ev.measured["volume_drift"])) < 1e-6 and str(ev.measured["schema"]).startswith("AP242")
    assert not ev.passed and ev.measured["freecad"] == "not installed"
