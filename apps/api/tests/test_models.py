import io
import json
import statistics
from pathlib import Path
from typing import Any

import pytest
import trimesh
from PIL import Image

from apps.api.tests.conftest import NO_REQS, REQS, Api, plate
from partwright_api import SerialGeometry, disk
from partwright_geometry import BuildError


def holes(api: Api, model_id: str, number: int) -> list[dict[str, Any]]:
    result = disk.version_dir(api.deps.settings.data_dir, model_id, number) / "result.json"
    found: list[dict[str, Any]] = json.loads(result.read_text(encoding="utf-8"))["artifact"]["parts"][0]["holes"]
    return found


def png_size(api: Api, url: str) -> tuple[int, int]:
    response = api.client.get(url)
    assert response.headers["content-type"] == "image/png"
    with Image.open(io.BytesIO(response.content)) as image:
        return image.size


def test_generated_model_lists_versions_with_metrics_files_and_thumbnail(api: Api) -> None:
    project = api.project()
    job = api.generate(project)
    assert job["status"] == "done", job
    model = api.ok(api.client.get(f"/models/{job['model_id']}"))
    assert (model["title"], model["latest_version"], model["versions"]) == ("Base plate", 1, 1)
    version = model["version"]
    assert version["origin"] == "generate" and version["status"] == "ok" and version["prompt"].startswith("Base plate")
    assert version["metrics"]["bbox"] == pytest.approx([120, 80, 5]) and version["metrics"]["holes"] == 4
    assert [c["passed"] for c in version["checks"]] == [True]
    assert {p["name"]: p["label"] for p in version["params"]}["bolt_spacing_x"] == "Bolt Spacing X"
    assert set(version["files"]) == {"step", "stl", "glb", "py", "ir"}
    assert png_size(api, version["thumbnail_url"]) == (256, 256)
    assert api.client.get(version["thumbnail_url"]).headers["cache-control"] == "no-cache"
    assert api.ok(api.client.get(f"/projects/{project}/models"))[0]["thumbnail_url"] == version["thumbnail_url"]
    assert api.ok(api.client.get(f"/projects/{project}"))["model_count"] == 1
    root = disk.version_dir(api.deps.settings.data_dir, job["model_id"], 1)
    assert {p.name for p in root.iterdir()} >= {
        "attempt_1",
        "steps.json",
        "params.json",
        "result.json",
        "OK",
        "model.step",
        "thumbnail.png",
    }


def test_export_formats_are_valid_files(api: Api, geometry: SerialGeometry, tmp_path: Path) -> None:
    model_id = api.generate(api.project())["model_id"]
    for fmt in ("step", "stl", "glb", "py", "ir"):
        response = api.client.get(f"/models/{model_id}/export", params={"fmt": fmt, "version": 1})
        assert response.status_code == 200, fmt
        (tmp_path / f"model.{fmt}").write_bytes(response.content)
    assert "attachment" in response.headers["content-disposition"]
    shape = geometry.describe(tmp_path / "model.step")
    assert shape.bbox_sorted == pytest.approx((5, 80, 120)) and shape.hole_diameters == pytest.approx([6.6] * 4)
    assert trimesh.load_mesh(tmp_path / "model.stl").is_watertight
    glb = tmp_path / "model.glb"
    assert glb.read_bytes()[:4] == b"glTF" and trimesh.load_scene(glb).extents == pytest.approx([0.12, 0.005, 0.08])
    volume = api.ok(api.client.get(f"/models/{model_id}/versions/1"))["metrics"]["volume"]
    assert shape.volume == pytest.approx(volume, rel=1e-6)
    assert json.loads((tmp_path / "model.ir").read_text())["title"] == "Base plate"
    assert api.client.get(f"/models/{model_id}/export", params={"fmt": "step", "version": 9}).status_code == 404


def test_params_patch_rebuilds_without_the_llm(api: Api) -> None:
    model_id = api.generate(api.project())["model_id"]
    calls = len(api.llm.calls)
    timings = []
    for spacing in (88, 89, 90):
        job = api.wait(api.ok(api.client.patch(f"/models/{model_id}/params", json={"values": {"bolt_spacing_x": spacing}}))["id"])
        assert (job["kind"], job["status"]) == ("params", "done"), job
        timings.append(job["steps"][-1]["elapsed_ms"])
    assert len(api.llm.calls) == calls
    xs = sorted({round(h["center"][0], 3) for h in holes(api, model_id, 4)})
    assert xs[1] - xs[0] == pytest.approx(90, abs=0.01)
    assert statistics.median(timings) < 1000, timings
    latest = api.ok(api.client.get(f"/models/{model_id}/versions/4"))
    assert latest["origin"] == "params" and latest["thumbnail_url"]
    assert [p["provenance"]["source"] for p in latest["params"] if p["name"] == "bolt_spacing_x"] == ["user_edit"]
    assert latest["changes"]["params"] == [{"name": "bolt_spacing_x", "old": 89.0, "new": 90.0}]


def test_bad_params_are_rejected_before_a_job_starts(api: Api) -> None:
    model_id = api.generate(api.project())["model_id"]
    assert api.client.patch(f"/models/{model_id}/params", json={"values": {"nope": 1}}).status_code == 400
    assert api.client.patch(f"/models/{model_id}/params", json={"values": {}}).status_code == 422
    assert api.client.patch("/models/nope/params", json={"values": {"width": 1}}).status_code == 404


def test_history_with_thumbnails_and_restore(api: Api) -> None:
    model_id = api.generate(api.project())["model_id"]
    for width in (90, 100, 110):
        api.wait(api.ok(api.client.patch(f"/models/{model_id}/params", json={"values": {"width": width}}))["id"])
    history = api.ok(api.client.get(f"/models/{model_id}/versions"))
    assert [v["number"] for v in history] == [1, 2, 3, 4]
    assert all(v["prompt"] and png_size(api, v["thumbnail_url"]) == (256, 256) for v in history)
    restored = api.ok(api.client.post(f"/models/{model_id}/versions/1/restore"))
    assert (restored["number"], restored["origin"]) == (5, "restore")
    assert restored["params"] == history[0]["params"]
    assert restored["changes"]["params"] == [{"name": "width", "old": 110.0, "new": 80.0}]
    assert api.client.post(f"/models/{model_id}/versions/9/restore").status_code == 404


def test_refine_makes_the_plate_thicker(api: Api) -> None:
    model_id = api.generate(api.project())["model_id"]
    api.llm.responses += [NO_REQS, json.dumps({"updates": [{"name": "thickness", "value": 15}], "design": None})]
    job = api.wait(api.ok(api.client.post(f"/models/{model_id}/refine", json={"instruction": "make it 10 mm thicker"}))["id"])
    assert job["status"] == "done", job
    version = api.ok(api.client.get(f"/models/{model_id}/versions/2"))
    assert version["origin"] == "refine" and version["metrics"]["bbox"][2] == pytest.approx(15, abs=0.01)
    assert api.client.post(f"/models/{model_id}/refine", json={"instruction": "x", "target": "nope"}).status_code == 400


def test_second_job_on_a_busy_model_is_409(api: Api) -> None:
    model_id = api.generate(api.project())["model_id"]
    api.llm.responses += [NO_REQS, json.dumps({"updates": [{"name": "thickness", "value": 6}], "design": None})]
    job = api.ok(api.client.post(f"/models/{model_id}/refine", json={"instruction": "6 mm thick"}))
    assert api.client.patch(f"/models/{model_id}/params", json={"values": {"width": 90}}).status_code == 409
    assert api.client.post(f"/models/{model_id}/versions/1/restore").status_code == 409
    api.wait(job["id"])


def test_missing_thumbnail_does_not_fail_the_job(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_gl(*_args: object) -> Path:
        raise BuildError("kernel", "OpenGL is not available")

    monkeypatch.setattr(api.deps.geometry, "thumbnail", no_gl)
    job = api.generate(api.project())
    version = api.ok(api.client.get(f"/models/{job['model_id']}/versions/1"))
    assert job["status"] == "done" and version["thumbnail_url"] is None
    assert api.client.get(f"/models/{job['model_id']}/versions/1/thumbnail").status_code == 404


def test_batch_runs_every_prompt(api: Api) -> None:
    project = api.project()
    for i in range(10):
        api.llm.responses += [REQS, plate(title=f"Plate {i}")]
    batch = api.ok(api.client.post("/batch", json={"project_id": project, "prompts": [f"Plate {i} 120 mm" for i in range(10)]}))
    jobs = [api.wait(j["id"]) for j in batch["jobs"]]
    assert [j["status"] for j in jobs] == ["done"] * 10
    models = api.ok(api.client.get(f"/projects/{project}/models"))
    assert sorted(m["title"] for m in models) == sorted(f"Plate {i}" for i in range(10))


def test_batch_variants_have_their_own_hole_counts(api: Api) -> None:
    project = api.project()
    for count_x in (2, 3, 4):
        api.llm.responses += [NO_REQS, plate(spacing_x=30, count_x=count_x)]
    prompts = [f"Base plate with {n} holes" for n in (4, 6, 8)]
    batch = api.ok(api.client.post("/batch", json={"project_id": project, "prompts": prompts}))
    counts = [api.ok(api.client.get(f"/models/{api.wait(j['id'])['model_id']}"))["version"]["metrics"]["holes"] for j in batch["jobs"]]
    assert counts == [4, 6, 8]


def test_variants_become_models_of_their_own(api: Api) -> None:
    project = api.project()
    base = api.generate(project)["model_id"]
    api.llm.responses.append(json.dumps({"param": "bolt_spacing_x", "values": [70, 80, 90]}))
    calls = len(api.llm.calls)
    batch = api.ok(api.client.post(f"/models/{base}/variants", json={"instruction": "3 versions with 70, 80 and 90 mm bolt spacing"}))
    assert len(api.llm.calls) == calls + 1
    jobs = [api.wait(j["id"]) for j in batch["jobs"]]
    assert [j["status"] for j in jobs] == ["done"] * 3 and len({j["model_id"] for j in jobs} | {base}) == 4
    spacings = []
    for job in jobs:
        xs = sorted({round(h["center"][0], 3) for h in holes(api, job["model_id"], 1)})
        spacings.append(xs[1] - xs[0])
    assert spacings == pytest.approx([70, 80, 90], abs=0.01)
    version = api.ok(api.client.get(f"/models/{jobs[0]['model_id']}/versions/1"))
    assert version["origin"] == "variant" and version["prompt"] == "bolt_spacing_x=70"
    sweep = api.ok(api.client.post(f"/models/{base}/variants", json={"param": "width", "values": [70, 75]}))
    assert [api.wait(j["id"])["status"] for j in sweep["jobs"]] == ["done", "done"]
    assert api.client.post(f"/models/{base}/variants", json={"param": "nope", "values": [1]}).status_code == 400
    assert api.client.post(f"/models/{base}/variants", json={}).status_code == 422
    assert len(api.ok(api.client.get(f"/projects/{project}/models"))) == 6


def test_suggestions_are_accepted_or_ignored(api: Api) -> None:
    model_id = api.generate(api.project())["model_id"]
    answer = {
        "suggestions": [
            {"target": "thickness", "change": {"thickness": 6}, "rationale": "stiffer plate"},
            {"target": "hole_d", "change": {"hole_d": 7}, "rationale": "looser fit"},
        ]
    }
    api.llm.responses.append(json.dumps(answer))
    made = api.ok(api.client.post(f"/models/{model_id}/suggestions"))
    expected = [("thickness", {"thickness": 6}, "open"), ("hole_d", {"hole_d": 7}, "open")]
    assert [(s["target"], s["change"], s["status"]) for s in made] == expected
    ir = api.client.get(f"/models/{model_id}/export", params={"fmt": "ir"}).content
    assert api.ok(api.client.post(f"/models/{model_id}/suggestions/{made[1]['id']}/ignore"))["status"] == "ignored"
    assert api.client.get(f"/models/{model_id}/export", params={"fmt": "ir"}).content == ir
    job = api.wait(api.ok(api.client.post(f"/models/{model_id}/suggestions/{made[0]['id']}/accept"))["id"])
    version = api.ok(api.client.get(f"/models/{model_id}/versions/{job['version']}"))
    assert version["origin"] == "suggestion" and version["metrics"]["bbox"][2] == pytest.approx(6)
    assert [s["status"] for s in api.ok(api.client.get(f"/models/{model_id}/suggestions"))] == ["accepted", "ignored"]
    assert api.client.post(f"/models/{model_id}/suggestions/{made[0]['id']}/accept").status_code == 409
    assert api.client.post(f"/models/{model_id}/suggestions/nope/ignore").status_code == 404


def test_thinking_level_reaches_the_model(api: Api) -> None:
    project = api.project()
    for level, budget in (("low", 0), ("high", 8192)):
        api.llm.responses += [REQS, plate()]
        job = api.wait(api.ok(api.client.post(f"/projects/{project}/generate", json={"prompt": "plate", "thinking": level}))["id"])
        assert job["status"] == "done" and api.llm.budgets[-1] == budget
        assert job["steps"][1]["message"].endswith(f"thinking {level} with a {budget} token reasoning budget")


def test_structure_lists_features_with_their_faces_and_params_and_is_cached(api: Api) -> None:
    job = api.generate(api.project())
    url = f"/models/{job['model_id']}/versions/1/structure"
    part = api.ok(api.client.get(url))["parts"][0]
    features = {f["id"]: f for f in part["features"]}
    assert sorted(i for f in features.values() for i in f["faces"]) == list(range(len(part["faces"])))
    assert (len(features["body"]["faces"]), len(features["holes"]["faces"])) == (6, 4)
    assert features["body"]["params"] == ["length", "width", "thickness"]
    assert "hole_d" in features["holes"]["params"] and "bolt_spacing_x" in features["holes"]["params"]
    assert part["explode"] is None
    assert (disk.version_dir(api.deps.settings.data_dir, job["model_id"], 1) / disk.STRUCTURE).exists()
    assert api.ok(api.client.get(url)) == {"parts": [part]}
