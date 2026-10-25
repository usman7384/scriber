from pathlib import Path

from partwright_geometry.service import failing_feature
from partwright_geometry.worker import handle


def test_model_code_cannot_import_os(tmp_path: Path) -> None:
    reply = handle({"source": "import os\ndef build(): return {}", "out_dir": str(tmp_path), "title": "x"})
    assert not reply["ok"] and "not allowed" in reply["error"]


def test_model_code_cannot_open_files(tmp_path: Path) -> None:
    reply = handle({"source": "def build():\n    open('x', 'w')\n    return {}", "out_dir": str(tmp_path), "title": "x"})
    assert not reply["ok"] and "open" in reply["error"]


def test_failing_line_maps_to_feature() -> None:
    helper = ["def _hole(part):", "    boom()", "", ""]
    part = ["def part_0():", "    part = None", "    # plate Plate", "    s = 1", "    # holes Holes", "    part = _hole(part)"]
    source = "\n".join(helper + part)
    assert failing_feature(source, [10, 2]) == "holes"
    assert failing_feature(source, [8]) == "plate"
    assert failing_feature(source, [2]) is None
