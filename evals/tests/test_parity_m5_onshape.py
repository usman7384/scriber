import json
from pathlib import Path

from scriber_agent import FakeLLM
from scriber_cli.config import load
from scriber_evals.parity import Rig, run_row
from scriber_evals.parity_m5_onshape import ROWS
from scriber_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]
NO_REQS = json.dumps({"requirements": []})
CHANGE = json.dumps({"updates": [{"name": "plate_thickness", "value": 10}, {"name": "bore_diameter", "value": 24}], "design": None})


def test_ap8_described_change_becomes_named_native_onshape_features(tmp_path: Path) -> None:
    geometry = LocalGeometry(timeout_s=300)
    try:
        ev = run_row("AP-8", ROWS["AP-8"], Rig(tmp_path, geometry, FakeLLM([NO_REQS, CHANGE]), load(ROOT / "config.yaml")))
    finally:
        geometry.close()
    assert ev.passed, ev
    assert ev.measured["import_calls"] == 0 and ev.measured["dangling_refs"] == 0
    assert ev.measured["changed"] == "bore_diameter 22 to 24, plate_thickness 6 to 10"
