from collections.abc import Iterator
from pathlib import Path

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals.parity import Rig, run_row
from partwright_evals.parity_m4_mission import ROWS
from partwright_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=300)
    yield g
    g.close()


@pytest.mark.parametrize("row", sorted(ROWS))
def test_mission_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run_row(row, ROWS[row], Rig(tmp_path, geometry, FakeLLM([]), load(ROOT / "config.yaml")))
    assert ev.passed, ev
