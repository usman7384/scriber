from collections.abc import Iterator
from pathlib import Path

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals.parity import Evidence, Rig, run_row
from partwright_evals.parity_m4_mesh import ROWS
from partwright_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()


def run(row: str, geometry: LocalGeometry, tmp_path: Path) -> Evidence:
    return run_row(row, ROWS[row], Rig(tmp_path, geometry, FakeLLM([]), load(ROOT / "config.yaml")))


@pytest.mark.parametrize("row", ["IN-7", "IN-8", "PF-5"])
def test_m4_mesh_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run(row, geometry, tmp_path)
    assert ev.passed, ev


def test_cd_4_reconstruction_passes_and_assembly_stays_pending(geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run("CD-4", geometry, tmp_path)
    assert ev.measured["reconstruction_passed"] is True, ev
    assert ev.measured["assembly"] == "pending" and not ev.passed
