import json
from pathlib import Path
from typing import Any

import pytest

from partwright_geometry.onshape import OnshapeRef, import_onshape
from partwright_ir import validate
from partwright_ir.model import Extrude, Polygon

REF = OnshapeRef(document="d1", workspace="w1", element="e1")
STUDIO = "/api/v10/partstudios/d/d1/w/w1/e/e1"


def line(x: float, y: float, dx: float, dy: float, length: float) -> dict[str, Any]:
    geometry = {"btType": "BTCurveGeometryLine-117", "pntX": x, "pntY": y, "dirX": dx, "dirY": dy}
    return {"btType": "BTMSketchCurveSegment-155", "startParam": 0.0, "endParam": length, "geometry": geometry}


def param(pid: str, **values: Any) -> dict[str, Any]:
    return {"parameterId": pid, **values}


SKETCH = {
    "featureType": "newSketch",
    "featureId": "S",
    "name": "Outline",
    "parameters": [param("sketchPlane", queries=[{"deterministicIds": ["JDC"]}])],
    # a triangle whose edges arrive out of order and partly reversed
    "entities": [line(0.02, 0.0, -1, 0, 0.02), line(0.0, 0.01, 0, -1, 0.01), line(0.0, 0.01, 1, -0.5, 0.02)],
}
EXTRUDE = {
    "featureType": "extrude",
    "featureId": "E",
    "name": "Pad",
    "parameters": [
        param("bodyType", value="SOLID"),
        param("operationType", value="NEW"),
        param("entities", queries=[{"featureId": "S"}]),
        param("endBound", value="BLIND"),
        param("depth", expression="0.25 in"),
    ],
}


class FakeApi:
    def __init__(self, features: list[dict[str, Any]], state: str = "DONE") -> None:
        self.replies = {
            f"GET {STUDIO}/features": {"features": features},
            "GET /api/v10/parts/d/d1/w/w1/e/e1": [{"name": "Wedge", "partId": "JHD"}],
            f"POST {STUDIO}/translations": {"id": "t1"},
            "GET /api/v10/translations/t1": {"requestState": state, "resultExternalDataIds": ["x1"]},
        }

    def get(self, path: str) -> bytes:
        return b"ISO-10303-21;" if path.endswith("/externaldata/x1") else json.dumps(self.replies[f"GET {path}"]).encode()

    def post(self, path: str, body: dict[str, Any]) -> bytes:
        return json.dumps(self.replies[f"POST {path}"]).encode()


def test_sketch_and_extrude_become_ir_and_other_features_are_listed(tmp_path: Path) -> None:
    fillet = {"featureType": "fillet", "featureId": "F", "name": "Fillet 1", "parameters": []}
    result = import_onshape(FakeApi([SKETCH, EXTRUDE, fillet]), REF, tmp_path / "s.step")
    (part,) = result.design.parts
    (polygon,) = part.sketches[0].entities
    assert isinstance(polygon, Polygon) and polygon.points == [(20.0, 0.0), (0.0, 0.0), (0.0, 10.0)]
    assert isinstance(part.features[0], Extrude) and part.features[0].distance == "pad_depth"
    assert result.design.params[0].value == pytest.approx(6.35)
    assert [(f.name, f.mapped_to) for f in result.features] == [("Outline", "outline"), ("Pad", "pad"), ("Fillet 1", None)]
    assert (part.name, result.bodies, validate(result.design)) == ("Wedge", ["Wedge"], [])


def test_open_profile_is_an_error(tmp_path: Path) -> None:
    sketch = SKETCH | {"entities": SKETCH["entities"][:2]}
    with pytest.raises(ValueError, match="open"):
        import_onshape(FakeApi([sketch, EXTRUDE]), REF, tmp_path / "s.step")


def test_unfinished_translation_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="ACTIVE"):
        import_onshape(FakeApi([SKETCH, EXTRUDE], state="ACTIVE"), REF, tmp_path / "s.step")
