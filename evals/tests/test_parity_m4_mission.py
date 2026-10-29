from collections.abc import Iterator
from pathlib import Path

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals.parity import Rig, run_row
from partwright_evals.parity_m4_mission import ROWS, variants
from partwright_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=300)
    yield g
    g.close()


def rig(geometry: LocalGeometry, tmp_path: Path) -> Rig:
    return Rig(tmp_path, geometry, FakeLLM([]), load(ROOT / "config.yaml"))


@pytest.mark.parametrize("row", sorted(set(ROWS) - {"PF-6"}))
def test_mission_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run_row(row, ROWS[row], rig(geometry, tmp_path))
    assert ev.passed, ev


def test_variant_sweep_rebuilds_every_variant(geometry: LocalGeometry, tmp_path: Path) -> None:
    # CI runs 16 variants, where worker start-up dominates; the 1,000-variant timing is the live PF-6 run
    ev = variants(rig(geometry, tmp_path), count=16, workers=2)
    assert (ev.measured["valid_single_solids"], ev.measured["distinct_volumes"]) == (16, 16), ev
