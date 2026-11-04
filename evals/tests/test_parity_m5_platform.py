import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from scriber_agent import FakeLLM
from scriber_cli.config import load
from scriber_evals.parity import Evidence, Rig, run_row
from scriber_evals.parity_m5_platform import ROWS
from scriber_evals.tools import FREECAD, PRUSASLICER, missing, tool
from scriber_geometry import LocalGeometry

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


def test_ex5_without_freecad_the_occt_round_trips_pass_and_the_row_stays_open(
    geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(FREECAD, raising=False)
    ev = run("EX-5", geometry, tmp_path)
    assert ev.measured["documented"] is True and ev.measured["freecad"] == missing(FREECAD), ev
    assert ev.measured["ap214_schema"] == "AUTOMOTIVE_DESIGN" and str(ev.measured["ap242_schema"]).startswith("AP242")
    assert float(str(ev.measured["ap242_occt_volume_drift"])) < 1e-6 and not ev.passed


@pytest.mark.skipif(not tool(FREECAD), reason=f"{FREECAD} is unset")
def test_ex5_both_step_flavours_round_trip_through_freecad(geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run("EX-5", geometry, tmp_path)
    assert ev.passed, ev
    assert ev.measured["ap214_freecad_solids"] == ev.measured["ap242_freecad_solids"] == 1


def test_vm9_without_the_tools_stays_open(geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(PRUSASLICER, raising=False)
    ev = run("VM-9", geometry, tmp_path)
    assert not ev.passed and ev.measured["prusaslicer"] == missing(PRUSASLICER)


@pytest.mark.skipif(not (tool(FREECAD) and tool(PRUSASLICER)), reason=f"{FREECAD} or {PRUSASLICER} is unset")
def test_vm9_five_fixtures_slice_and_open_as_one_solid(geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run("VM-9", geometry, tmp_path)
    assert ev.passed, ev
    assert sum(k.startswith("b") and not k.endswith("_log") for k in ev.measured) == 5
