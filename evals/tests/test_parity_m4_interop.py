from collections.abc import Iterator
from pathlib import Path

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals.parity import Evidence, Rig, run_row
from partwright_evals.parity_m4_interop import ROWS
from partwright_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=300)
    yield g
    g.close()


def run(row: str, geometry: LocalGeometry, out: Path) -> Evidence:
    return run_row(row, ROWS[row], Rig(out, geometry, FakeLLM([]), load(ROOT / "config.yaml")))


@pytest.mark.parametrize("row", ["GE-12", "GE-3", "IN-10"])
def test_interop_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run(row, geometry, tmp_path)
    assert ev.passed, ev


def test_ex4_bundle_half_passes_and_the_fcstd_half_stays_open(geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run("EX-4", geometry, tmp_path)
    assert ev.measured["bundle_ok"] is True, ev
    assert not ev.passed and "FCStd" in ev.note
