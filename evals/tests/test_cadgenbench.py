import json
from pathlib import Path

from build123d import Box, Pos, export_step, import_step

from scriber_agent import FakeLLM, Result, Step
from scriber_evals.cadgenbench import Fixture, attempt, fixtures, kept_step, last_built, orient, salvage
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
    match = json.dumps({"findings": [], "matches": True})
    llm = FakeLLM([NO_REQS, NO_REQS, REFERENCE.read_text(encoding="utf-8"), match])
    try:
        run, work = tmp_path / "run", tmp_path / "work"
        built = attempt(Fixture(id="101", prompt="Reproduce it.", images=[image], editing=False), llm, llm, geometry, run, work, 0)
        skipped = attempt(Fixture(id="201", prompt="Edit it.", images=[], editing=True), llm, llm, geometry, run, work, 0)
    finally:
        geometry.close()
    assert built.status == "built" and (tmp_path / "run" / "101" / "output.step").stat().st_size > 0
    assert llm.calls[1][-1].images == llm.calls[2][-1].images == (PNG,)
    assert skipped.status == "skipped"


def test_the_newest_built_attempt_is_submitted_even_after_later_failures(tmp_path: Path) -> None:
    for n, built in ((1, True), (2, False), (10, True), (11, False)):
        d = tmp_path / f"attempt_{n}"
        d.mkdir()
        if built:
            (d / "model.step").write_text("step", encoding="utf-8")
    assert last_built(tmp_path) == tmp_path / "attempt_10" / "model.step"
    assert last_built(tmp_path / "attempt_2") is None


def test_an_error_after_a_built_attempt_still_submits_it(tmp_path: Path) -> None:
    run, work = tmp_path / "run", tmp_path / "work"
    (run / "143").mkdir(parents=True)
    (work / "143" / "attempt_3").mkdir(parents=True)
    export_step(Box(30, 20, 10), work / "143" / "attempt_3" / "model.step")
    kept = salvage("143", run, work, "RemoteProtocolError: peer closed connection")
    assert kept.status == "built (attempt_3), then error" and kept.attempts == 3
    assert (run / "143" / "output.step").is_file()
    assert salvage("150", run, work, "boom").status == "error"


def test_the_submitted_attempt_is_the_one_the_loop_kept(tmp_path: Path) -> None:
    for n in (1, 3):
        (tmp_path / f"attempt_{n}").mkdir()
        export_step(Box(10, 10, 10), tmp_path / f"attempt_{n}" / "model.step")

    def ended(kept: int) -> list[Step]:
        result = Result(design=None, artifact=None, checks=[], attempts=kept, repairs=0)
        return [Step(kind="failed", message="gave up", attempt=3, elapsed_ms=0, result=result)]

    assert kept_step(tmp_path, ended(1)) == tmp_path / "attempt_1" / "model.step"
    assert kept_step(tmp_path, ended(2)) == tmp_path / "attempt_3" / "model.step"  # kept one has no STEP: newest built
    assert kept_step(tmp_path, []) == tmp_path / "attempt_3" / "model.step"
