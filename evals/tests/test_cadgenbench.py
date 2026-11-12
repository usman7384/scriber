import json
from pathlib import Path

from build123d import Box, Pos, export_step, import_step

from scriber_agent import FakeLLM
from scriber_evals.cadgenbench import Fixture, attempt, fixtures, orient
from scriber_geometry import LocalGeometry

REFERENCE = Path(__file__).parents[1] / "parity" / "m6" / "reference" / "sc15-hub-gear.json"
NO_REQS = json.dumps({"requirements": []})
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 8


def fixture_dir(root: Path, fid: str, input_type: str, files: list[str]) -> None:
    d = root / fid
    d.mkdir(parents=True)
    spec = {"description": "Reproduce the geometry.\n", "input_files": files, "input_type": input_type}
    (d / "description.yaml").write_text(json.dumps(spec), encoding="utf-8")
    for name in files:
        (d / name).write_bytes(PNG)


def test_fixtures_split_generation_from_editing(tmp_path: Path) -> None:
    fixture_dir(tmp_path, "101", "text+image", ["input.png", "input2.png"])
    fixture_dir(tmp_path, "201", "text+step", ["input.step"])
    (tmp_path / "sanity_check_submission.py").write_text("", encoding="utf-8")
    found = list(fixtures(tmp_path))
    assert [(f.id, f.editing, len(f.images)) for f in found] == [("101", False, 2), ("201", True, 0)]
    assert found[0].prompt == "Reproduce the geometry."


def test_orient_centres_and_orders_extents(tmp_path: Path) -> None:
    export_step(Pos(7, -3, 2) * Box(10, 30, 5), tmp_path / "in.step")
    orient(tmp_path / "in.step", tmp_path / "out.step")
    box = import_step(tmp_path / "out.step").bounding_box()
    assert [round(v, 6) for v in (box.size.X, box.size.Y, box.size.Z)] == [30, 10, 5]
    assert box.center().length < 1e-6


def test_generation_writes_an_oriented_step_and_editing_is_skipped(tmp_path: Path) -> None:
    geometry = LocalGeometry(timeout_s=300)
    image = tmp_path / "input.png"
    image.write_bytes(PNG)
    llm = FakeLLM([NO_REQS, REFERENCE.read_text(encoding="utf-8")])
    try:
        run, work = tmp_path / "run", tmp_path / "work"
        built = attempt(Fixture(id="101", prompt="Reproduce it.", images=[image], editing=False), llm, llm, geometry, run, work, 0)
        skipped = attempt(Fixture(id="201", prompt="Edit it.", images=[], editing=True), llm, llm, geometry, run, work, 0)
    finally:
        geometry.close()
    assert built.status == "built" and (tmp_path / "run" / "101" / "output.step").stat().st_size > 0
    assert llm.calls[1][-1].images == (PNG,)
    assert skipped.status == "skipped"
