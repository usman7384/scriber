import math
from collections.abc import Iterator
from pathlib import Path

import pytest

from scriber_agent import FakeLLM
from scriber_cli.config import load
from scriber_evals.parity import Rig, run_row
from scriber_evals.parity_m4_aircraft import ROWS, fit_section
from scriber_geometry import LocalGeometry
from scriber_ir.airfoil import naca4

ROOT = Path(__file__).parents[2]


def placed(naca: str, chord: float, le: tuple[float, float], incidence: float) -> list[tuple[float, float, float]]:
    c, s = math.cos(math.radians(-incidence)), math.sin(math.radians(-incidence))
    return [(le[0] + chord * (x * c - z * s), 0.0, le[1] + chord * (x * s + z * c)) for x, z in naca4(naca, 150)]


def test_fit_recovers_chord_position_and_incidence() -> None:
    fit = fit_section(placed("2412", 180, (40, 12), 3), "2412")
    assert (fit.chord, fit.le_x, fit.le_z, fit.incidence) == pytest.approx((180, 40, 12, 3), abs=0.02)
    assert fit.deviation_pct < 0.02


def test_fit_rejects_the_wrong_airfoil() -> None:
    assert fit_section(placed("0012", 180, (0, 0), 0), "2412").deviation_pct > 0.5


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=300)
    yield g
    g.close()


@pytest.mark.parametrize("row", sorted(ROWS))
def test_aircraft_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run_row(row, ROWS[row], Rig(tmp_path, geometry, FakeLLM([]), load(ROOT / "config.yaml")))
    assert ev.passed, ev
