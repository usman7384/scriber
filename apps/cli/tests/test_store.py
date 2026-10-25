from pathlib import Path

import pytest

from partwright_agent import Result
from partwright_cli import store
from partwright_geometry import Artifact, PartMetrics
from partwright_ir import Design

DESIGN = Design.model_validate(
    {
        "title": "Plate",
        "params": [{"name": "t", "value": 5, "unit": "mm"}],
        "parts": [
            {
                "id": "p",
                "name": "P",
                "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": 10, "height": 10}]}],
                "features": [{"kind": "extrude", "id": "e", "name": "E", "sketch": "s", "distance": "t"}],
            }
        ],
    }
)


def result(tmp: Path, valid: bool) -> Result:
    (tmp / "design.json").write_text(DESIGN.model_dump_json(), encoding="utf-8")
    part = PartMetrics(id="p", name="P", volume=1, bbox_min=(0, 0, 0), bbox_size=(1, 1, 1), solids=1, faces=6, valid=valid, holes=[])
    findings = [] if valid else [{"rule_id": "GEO-VALID", "severity": "error", "message": "bad"}]
    art = Artifact.model_validate(
        {"design_hash": "x", "files": {"ir": tmp / "design.json"}, "parts": [part], "findings": findings, "elapsed_ms": 1}
    )
    return Result(design=DESIGN, artifact=art, checks=[], attempts=1, repairs=0)


def test_latest_design_skips_failed_versions(tmp_path: Path) -> None:
    for name, valid in (("v1", True), ("v2", False)):
        work = tmp_path / f"work_{name}"
        work.mkdir()
        store.save(tmp_path / name, [], result(work, valid))
    assert store.next_version(tmp_path).name == "v3"
    assert store.latest_design(tmp_path) == DESIGN
    (tmp_path / "v1" / store.OK_MARKER).unlink()
    with pytest.raises(FileNotFoundError):
        store.latest_design(tmp_path)
