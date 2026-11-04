import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any

import pytest

from apps.api.tests.conftest import Api, MakeApi, plate
from apps.api.tests.test_designs import post_design
from scriber_geometry import SliceReport

FREECAD = os.environ.get("SCRIBER_FREECAD")
PRUSASLICER = os.environ.get("SCRIBER_PRUSASLICER")
FAKE = Path("tool.exe")
REPORT = SliceReport(exit_code=0, manifold=True, layers=17, gcode_bytes=4096, warnings=[], errors=[])


def plate_model(api: Api, design: str = plate()) -> str:
    job = post_design(api, api.project(), design)
    assert job["status"] == "done", job
    model_id: str = job["model_id"]
    return model_id


def fake_freecad(monkeypatch: pytest.MonkeyPatch, errors: list[str]) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []

    def run(_freecad: Path, _script: str, args: dict[str, Any]) -> dict[str, Any]:
        plans.append(args)
        Path(args["out"]).write_bytes(b"PK fcstd")
        return {"errors": errors}

    monkeypatch.setattr("scriber_geometry.fcstd.run_freecad", run)
    return plans


def test_health_lists_the_configured_tools(make_api: MakeApi) -> None:
    assert make_api().ok(make_api().client.get("/health"))["tools"] == {"freecad": False, "prusaslicer": False}
    configured = make_api(freecad=FAKE, prusaslicer=FAKE)
    assert configured.ok(configured.client.get("/health"))["tools"] == {"freecad": True, "prusaslicer": True}


def test_tool_routes_say_when_the_tool_is_not_configured(api: Api) -> None:
    model_id = plate_model(api)
    export = api.client.get(f"/models/{model_id}/export", params={"fmt": "fcstd"})
    sliced = api.client.post(f"/models/{model_id}/slice")
    assert export.status_code == 503 and "SCRIBER_FREECAD" in export.json()["detail"]
    assert sliced.status_code == 503 and "SCRIBER_PRUSASLICER" in sliced.json()["detail"]


def test_fcstd_export_sends_the_version_plan_to_freecad(make_api: MakeApi, monkeypatch: pytest.MonkeyPatch) -> None:
    api = make_api(freecad=FAKE)
    plans = fake_freecad(monkeypatch, [])
    response = api.client.get(f"/models/{plate_model(api)}/export", params={"fmt": "fcstd", "version": 1})
    assert response.status_code == 200 and response.content == b"PK fcstd"
    assert 'filename="base-plate-v1.FCStd"' in response.headers["content-disposition"]
    [plan] = plans
    assert [p["name"] for p in plan["params"]] == ["length", "width", "thickness", "hole_d", "bolt_spacing_x"]
    assert [o["label"] for o in plan["bodies"][0]["objects"] if o["type"] != "Sketcher::SketchObject"] == ["Plate", "Bolt holes"]


def test_fcstd_export_names_the_unsupported_construct(make_api: MakeApi, monkeypatch: pytest.MonkeyPatch) -> None:
    api = make_api(freecad=FAKE)
    plans = fake_freecad(monkeypatch, [])
    design = json.loads(plate())
    design["parts"][0]["features"].append({"kind": "fillet", "id": "round", "name": "Round", "edges": {}, "radius": 1})
    response = api.client.get(f"/models/{plate_model(api, json.dumps(design))}/export", params={"fmt": "fcstd"})
    assert response.status_code == 422 and "fillet feature 'round'" in response.json()["detail"]
    assert plans == []


def test_fcstd_export_reports_a_freecad_failure(make_api: MakeApi, monkeypatch: pytest.MonkeyPatch) -> None:
    api = make_api(freecad=FAKE)
    fake_freecad(monkeypatch, ["Pad failed"])
    response = api.client.get(f"/models/{plate_model(api)}/export", params={"fmt": "fcstd"})
    assert response.status_code == 502 and "Pad failed" in response.json()["detail"]


def test_slice_reports_printability_of_the_version_stl(make_api: MakeApi, monkeypatch: pytest.MonkeyPatch) -> None:
    api = make_api(prusaslicer=FAKE)
    sliced: list[Path] = []

    def slice_stl(_slicer: Path, stl: Path, _gcode: Path) -> SliceReport:
        sliced.append(stl)
        return REPORT

    monkeypatch.setattr("scriber_api.tools.slice_stl", slice_stl)
    model_id = plate_model(api)
    report = api.ok(api.client.post(f"/models/{model_id}/slice", params={"version": 1}))
    assert report == {"model_id": model_id, "version": 1, "ok": True, **REPORT.model_dump()}
    assert sliced[0].name == "model.stl" and sliced[0].parent.name == "v1"
    assert api.client.post(f"/models/{model_id}/slice", params={"version": 9}).status_code == 404


@pytest.mark.skipif(not FREECAD, reason="SCRIBER_FREECAD is unset")
def test_fcstd_export_with_freecad(make_api: MakeApi) -> None:
    api = make_api(freecad=Path(str(FREECAD)))
    response = api.client.get(f"/models/{plate_model(api)}/export", params={"fmt": "fcstd"})
    assert response.status_code == 200, response.text
    assert "Document.xml" in zipfile.ZipFile(io.BytesIO(response.content)).namelist()


@pytest.mark.skipif(not PRUSASLICER, reason="SCRIBER_PRUSASLICER is unset")
def test_slice_with_prusaslicer(make_api: MakeApi) -> None:
    api = make_api(prusaslicer=Path(str(PRUSASLICER)))
    report = api.ok(api.client.post(f"/models/{plate_model(api)}/slice"))
    assert report["ok"] and report["manifold"] and report["layers"] > 0 and report["gcode_bytes"] > 0
