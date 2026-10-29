from collections.abc import Iterator
from pathlib import Path

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals.parity import Evidence, Rig, run_row
from partwright_evals.parity_m4_interop import ROWS
from partwright_evals.tools import FREECAD, missing, tool
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


def test_ex4_without_freecad_the_bundle_and_onshape_halves_pass_and_the_row_stays_open(
    geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(FREECAD, raising=False)
    ev = run("EX-4", geometry, tmp_path)
    assert ev.measured["bundle_ok"] is True and ev.measured["onshape_ok"] is True, ev
    assert ev.measured["fcstd_reference_designs"] == "26/30 map to PartDesign"
    assert not ev.passed and ev.measured["freecad"] == missing(FREECAD)


@pytest.mark.skipif(not tool(FREECAD), reason=f"{FREECAD} is unset")
def test_ex4_fcstd_reopens_with_named_constrained_history_that_parameters_drive(geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run("EX-4", geometry, tmp_path)
    assert ev.passed, ev
    assert ev.measured["bracket_params_driving_the_model"] == "7/7" and ev.measured["flange_params_driving_the_model"] == "7/7"
