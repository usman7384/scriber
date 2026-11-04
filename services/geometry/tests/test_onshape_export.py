import json
from pathlib import Path
from typing import Any

import pytest

from scriber_geometry.onshape import OnshapeRef, RecordedOnshape, import_onshape
from scriber_geometry.onshape_export import UnsupportedExportError, export_onshape
from scriber_ir import Design
from scriber_ir.model import Circle, Polygon

STUDIO = "/api/v10/partstudios/d/D/w/W/e/E"


class Studio:
    def __init__(self, status: str = "OK") -> None:
        self.status = status
        self.features: list[dict[str, Any]] = []

    def get(self, path: str) -> bytes:
        replies = {
            f"{STUDIO}/features": {"features": self.features},
            "/api/v10/parts/d/D/w/W/e/E": [{"name": "Puck"}],
            "/api/v10/translations/t": {"requestState": "DONE", "resultExternalDataIds": ["x"]},
        }
        return b"ISO-10303-21;" if path.endswith("/externaldata/x") else json.dumps(replies[path]).encode()

    def post(self, path: str, body: dict[str, Any]) -> bytes:
        if path.endswith("/documents"):
            return json.dumps({"id": "D", "defaultWorkspace": {"id": "W"}}).encode()
        if path.endswith("/translations"):
            return json.dumps({"id": "t"}).encode()
        if not path.endswith("/features"):
            return json.dumps({"id": "E"}).encode()
        feature = body["feature"] | {"featureId": f"F{len(self.features)}"}
        self.features.append(feature)
        return json.dumps({"feature": feature, "featureState": {"featureStatus": self.status}}).encode()


def design(sketch: dict[str, Any], *features: dict[str, Any]) -> Design:
    extrude = {"kind": "extrude", "id": "pad", "name": "Pad", "sketch": "s", "distance": 5}
    params = [{"name": "t", "value": 4, "unit": "mm"}, {"name": "h", "value": 3, "unit": "mm"}]
    part = {"id": "p", "name": "Puck", "sketches": [{"id": "s", **sketch}], "features": [extrude, *features]}
    return Design.model_validate({"title": "Puck", "params": params, "parts": [part]})


def test_exported_sketches_and_extrudes_read_back_through_the_importer(tmp_path: Path) -> None:
    square = {"kind": "rect", "center": [10, 0], "width": 20, "height": 8}
    api = Studio()
    export_onshape(api, design({"entities": [square, {"kind": "circle", "center": [40, 0], "diameter": 6}]}))
    (part,) = import_onshape(api, OnshapeRef(document="D", workspace="W", element="E"), tmp_path / "p.step").design.parts
    polygon, circle = part.sketches[0].entities
    assert isinstance(polygon, Polygon) and polygon.points == [(0.0, -4.0), (20.0, -4.0), (20.0, 4.0), (0.0, 4.0)]
    assert isinstance(circle, Circle) and (circle.center, circle.diameter) == ((40.0, 0.0), 6.0)
    assert [f.name for f in part.features] == ["Pad"]


def test_offset_planes_are_created_once_and_expressions_link_variables() -> None:
    plane = {"ref": "XY", "offset": "t + h"}
    hole = {"kind": "hole", "id": "bore", "name": "Bore", "plane": plane, "at": {"kind": "points", "points": [[0, 0]]}, "diameter": "t"}
    api = Studio()
    made = export_onshape(api, design({"plane": plane, "entities": [{"kind": "circle", "diameter": 9}]}, hole))
    assert [(f.name, f.type) for f in made.features if f.type not in ("assignVariable",)] == [
        ("s plane", "cPlane"),
        ("s", "newSketch"),
        ("Pad", "extrude"),
        ("bore locations", "newSketch"),
        ("Bore", "hole"),
    ]
    quantities = {p["parameterId"]: p["expression"] for f in api.features for p in f["parameters"] if "expression" in p}
    assert (quantities["offset"], quantities["depth"], quantities["holeDiameter"]) == ("#t + #h", "5.0 mm", "#t")


@pytest.mark.parametrize(
    ("sketch", "match"),
    [
        ({"entities": [{"kind": "rect", "width": 5, "height": 5, "corner_radius": 1}]}, "rect is not exported"),
        ({"plane": {"ref": "pad.end"}, "entities": [{"kind": "circle", "diameter": 2}]}, "not XY, XZ or YZ"),
        ({"entities": [{"kind": "circle", "diameter": 2, "subtract": True}]}, "subtracted"),
    ],
)
def test_unsupported_geometry_fails_fast(sketch: dict[str, Any], match: str) -> None:
    with pytest.raises(UnsupportedExportError, match=match):
        export_onshape(Studio(), design(sketch))


def test_unsupported_feature_and_rejected_feature_are_errors() -> None:
    circle = {"entities": [{"kind": "circle", "diameter": 9}]}
    fillet = {"kind": "fillet", "id": "round", "name": "Round", "edges": {}, "radius": 1}
    with pytest.raises(UnsupportedExportError, match="fillet"):
        export_onshape(Studio(), design(circle, fillet))
    with pytest.raises(RuntimeError, match="ERROR"):
        export_onshape(Studio("ERROR"), design(circle))


def test_recorded_replay_answers_repeated_calls_in_order(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text("1")
    (tmp_path / "b.json").write_text("2")
    (tmp_path / "recording.json").write_text(json.dumps({"POST /x": ["a.json", "b.json"]}))
    api = RecordedOnshape(tmp_path)
    assert [api.post("/x", {"n": 1}), api.post("/x", {"n": 2})] == [b"1", b"2"]
    assert api.posts == [("/x", {"n": 1}), ("/x", {"n": 2})]
    with pytest.raises(KeyError, match="only 2"):
        api.post("/x", {})
