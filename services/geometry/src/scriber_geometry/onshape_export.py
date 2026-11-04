import json
import math
import re
from dataclasses import dataclass, field
from typing import Any

from scriber_geometry.models import Frozen
from scriber_geometry.onshape import API, PLANES, OnshapeApi
from scriber_ir import Design, Param, evaluate
from scriber_ir.fasteners import hole_size
from scriber_ir.model import Circle, Entity, Expr, Extrude, Hole, Part, PlaneRef, Polygon, Rect
from scriber_ir.placement import hole_centres

Json = dict[str, Any]
Point2 = tuple[float, float]
DEFAULT_PLANES = {plane: deterministic for deterministic, plane in PLANES.items()}
VARIABLE = {"mm": ("LENGTH", "lengthValue"), "deg": ("ANGLE", "angleValue"), "": ("NUMBER", "numberValue")}
OPERATION = {"add": "ADD", "cut": "REMOVE", "intersect": "INTERSECT"}
BOUND = {"blind": "BLIND", "symmetric": "BLIND", "through_all": "THROUGH_ALL", "up_to_next": "UP_TO_NEXT"}
HOLE_STYLE = {"simple": "SIMPLE", "tapped": "SIMPLE", "counterbore": "C_BORE", "countersink": "C_SINK"}
SUM_OF_NAMES = re.compile(r"^[a-z][a-z0-9_]*(\s*[-+]\s*[a-z][a-z0-9_]*)*$")
NAME = re.compile(r"[a-z][a-z0-9_]*")


class UnsupportedExportError(ValueError):
    pass


class ExportedFeature(Frozen):
    feature_id: str
    name: str
    type: str
    status: str


class OnshapeExport(Frozen):
    document: str
    workspace: str
    studios: dict[str, str]
    features: list[ExportedFeature]


@dataclass
class _Studio:
    api: OnshapeApi
    path: str
    values: dict[str, float]
    made: list[ExportedFeature] = field(default_factory=list)
    planes: dict[tuple[str, str], Json] = field(default_factory=dict)

    def add(self, feature: Json) -> str:
        reply = _post(self.api, self.path, {"btType": "BTFeatureDefinitionCall-1406", "feature": feature})
        status = reply["featureState"]["featureStatus"]
        if status != "OK":
            raise RuntimeError(f"Onshape answered {status} for feature {feature['name']!r}")
        fid = reply["feature"]["featureId"]
        self.made.append(ExportedFeature(feature_id=fid, name=feature["name"], type=feature["featureType"], status=status))
        return str(fid)

    def length(self, e: Expr) -> str:
        if isinstance(e, str) and SUM_OF_NAMES.match(e) and all(n in self.values for n in NAME.findall(e)):
            return NAME.sub(lambda m: f"#{m[0]}", e)
        return f"{evaluate(e, self.values)!r} mm"

    def plane(self, ref: PlaneRef, name: str) -> Json:
        if ref.ref not in DEFAULT_PLANES:
            raise UnsupportedExportError(f"{name}: plane {ref.ref!r} is not XY, XZ or YZ; face and datum planes are not exported")
        base = {"btType": "BTMIndividualQuery-138", "deterministicIds": [DEFAULT_PLANES[ref.ref]]}
        if evaluate(ref.offset, self.values) == 0:
            return base
        key = (ref.ref, str(ref.offset))
        if key not in self.planes:
            offset = [_enum("cplaneType", "CPlaneType", "OFFSET"), _query("entities", base), _quantity("offset", self.length(ref.offset))]
            fid = self.add(_feature("cPlane", f"{name} plane", offset))
            self.planes[key] = {"btType": "BTMIndividualCreatedByQuery-137", "featureId": fid, "entityType": "FACE"}
        return self.planes[key]


def export_onshape(api: OnshapeApi, design: Design) -> OnshapeExport:
    doc = _post(api, f"{API}/documents", {"name": design.title, "isPublic": False})
    did, wid = doc["id"], doc["defaultWorkspace"]["id"]
    studios: dict[str, str] = {}
    made: list[ExportedFeature] = []
    for part in design.parts:
        eid = _post(api, f"{API}/partstudios/d/{did}/w/{wid}", {"name": part.name})["id"]
        studio = _Studio(api, f"{API}/partstudios/d/{did}/w/{wid}/e/{eid}/features", design.param_values())
        _export_part(studio, design.params, part)
        studios[part.id], made = eid, made + studio.made
    return OnshapeExport(document=did, workspace=wid, studios=studios, features=made)


def _export_part(studio: _Studio, params: list[Param], part: Part) -> None:
    for p in params:
        studio.add(_variable(p))
    sketches = {s.id: s for s in part.sketches}
    made: dict[str, str] = {}
    for f in part.features:
        match f:
            case Extrude():
                sketch = sketches[f.sketch]
                if sketch.id not in made:
                    lines = [e for i, x in enumerate(sketch.entities) for e in _entity(f"{sketch.id}.{i}", x, studio.values)]
                    made[sketch.id] = studio.add(_sketch(sketch.id, studio.plane(sketch.plane, sketch.id), lines))
                first = not any(m.type == "extrude" for m in studio.made)
                studio.add(_extrude(studio, f, made[sketch.id], first))
            case Hole():
                points = [_point(f"{f.id}.{i}", c) for i, c in enumerate(hole_centres(f, studio.values))]
                sid = studio.add(_sketch(f"{f.id} locations", studio.plane(f.plane, f.id), points))
                studio.add(_hole(studio, f, sid))
            case _:
                raise UnsupportedExportError(f"{f.kind} feature {f.id!r} has no Onshape export yet")


def _variable(p: Param) -> Json:
    kind, slot = VARIABLE[p.unit]
    value = f"{p.value!r} {p.unit}".strip()
    params = [_enum("variableType", "VariableType", kind), _string("name", p.name), _quantity(slot, value)]
    return _feature("assignVariable", p.name, params)


def _extrude(studio: _Studio, f: Extrude, sketch: str, first: bool) -> Json:
    if f.extent not in BOUND or evaluate(f.taper, studio.values) != 0:
        raise UnsupportedExportError(f"extrude {f.id!r}: {f.extent} extents and tapers are not exported")
    operation = "NEW" if first and f.mode == "add" else OPERATION[f.mode]
    region = {"btType": "BTMIndividualSketchRegionQuery-140", "featureId": sketch}
    params = [
        _enum("bodyType", "ToolBodyType", "SOLID"),
        _enum("operationType", "NewBodyOperationType", operation),
        _query("entities", region),
        _enum("endBound", "BoundingType", BOUND[f.extent]),
    ]
    if f.extent in ("blind", "symmetric"):
        params.append(_quantity("depth", studio.length(f.distance or 0.0)))
    # the IR's through_all from a base plane cuts both ways
    if f.extent in ("symmetric", "through_all"):
        params.append(_boolean("symmetric", True))
    return _feature("extrude", f.name, params)


def _hole(studio: _Studio, f: Hole, locations: str) -> Json:
    size = hole_size(f, studio.values)
    diameter = studio.length(f.diameter) if f.diameter is not None else f"{size.diameter!r} mm"
    params = [
        _enum("style", "HoleStyle", HOLE_STYLE[f.type]),
        _enum("endStyle", "HoleEndStyle", "THROUGH" if f.depth is None else "BLIND"),
        _quantity("holeDiameter", diameter),
        _query("locations", {"btType": "BTMIndividualCreatedByQuery-137", "featureId": locations, "entityType": "VERTEX"}),
    ]
    if f.depth is not None:
        params.append(_quantity("holeDepth", studio.length(f.depth)))
    if size.cb_diameter is not None and size.cb_depth is not None:
        params += [_quantity("cBoreDiameter", f"{size.cb_diameter!r} mm"), _quantity("cBoreDepth", f"{size.cb_depth!r} mm")]
    if size.cs_diameter is not None:
        angle = f"{evaluate(f.cs_angle, studio.values)!r} deg"
        params += [_quantity("cSinkDiameter", f"{size.cs_diameter!r} mm"), _quantity("cSinkAngle", angle)]
    return _feature("hole", f.name, params)


def _entity(eid: str, e: Entity, values: dict[str, float]) -> list[Json]:
    def v(x: Expr) -> float:
        return evaluate(x, values)

    if e.subtract:
        raise UnsupportedExportError(f"sketch entity {eid}: subtracted profiles are not exported")
    match e:
        case Rect() if v(e.corner_radius) == 0:
            cx, cy, w, h = v(e.center[0]), v(e.center[1]), v(e.width) / 2, v(e.height) / 2
            return _loop(eid, [(cx - w, cy - h), (cx + w, cy - h), (cx + w, cy + h), (cx - w, cy + h)])
        case Polygon():
            return _loop(eid, [(v(x), v(y)) for x, y in e.points])
        case Circle():
            geometry = {"btType": "BTCurveGeometryCircle-115", "radius": _m(v(e.diameter) / 2), "clockwise": False}
            centre = {"xCenter": _m(v(e.center[0])), "yCenter": _m(v(e.center[1])), "xDir": 1.0, "yDir": 0.0}
            return [{"btType": "BTMSketchCurve-4", "entityId": eid, "centerId": f"{eid}.center", "geometry": geometry | centre}]
    raise UnsupportedExportError(f"sketch entity {eid}: {e.kind} is not exported (rounded rects, slots and paths need arcs)")


def _loop(eid: str, points: list[Point2]) -> list[Json]:
    return [_line(f"{eid}.{i}", a, points[(i + 1) % len(points)]) for i, a in enumerate(points)]


def _line(eid: str, a: Point2, b: Point2) -> Json:
    length = math.dist(a, b)
    direction = {"dirX": (b[0] - a[0]) / length, "dirY": (b[1] - a[1]) / length}
    geometry = {"btType": "BTCurveGeometryLine-117", "pntX": _m(a[0]), "pntY": _m(a[1])} | direction
    ends = {"startPointId": f"{eid}.start", "endPointId": f"{eid}.end", "startParam": 0.0, "endParam": _m(length)}
    return {"btType": "BTMSketchCurveSegment-155", "entityId": eid, **ends, "geometry": geometry}


def _point(eid: str, p: Point2) -> Json:
    return {"btType": "BTMSketchPoint-158", "entityId": eid, "x": _m(p[0]), "y": _m(p[1]), "isConstruction": False}


def _sketch(name: str, plane: Json, entities: list[Json]) -> Json:
    head = {"btType": "BTMSketch-151", "featureType": "newSketch", "name": name, "parameters": [_query("sketchPlane", plane)]}
    return head | {"entities": entities, "constraints": []}


def _feature(kind: str, name: str, params: list[Json]) -> Json:
    return {"btType": "BTMFeature-134", "featureType": kind, "name": name, "parameters": params}


def _enum(pid: str, enum: str, value: str) -> Json:
    return {"btType": "BTMParameterEnum-145", "parameterId": pid, "enumName": enum, "value": value}


def _quantity(pid: str, expression: str) -> Json:
    return {"btType": "BTMParameterQuantity-147", "parameterId": pid, "expression": expression}


def _string(pid: str, value: str) -> Json:
    return {"btType": "BTMParameterString-149", "parameterId": pid, "value": value}


def _boolean(pid: str, value: bool) -> Json:
    return {"btType": "BTMParameterBoolean-144", "parameterId": pid, "value": value}


def _query(pid: str, query: Json) -> Json:
    return {"btType": "BTMParameterQueryList-148", "parameterId": pid, "queries": [query]}


def _post(api: OnshapeApi, path: str, body: Json) -> Json:
    reply: Json = json.loads(api.post(path, body))
    return reply


def _m(mm: float) -> float:
    return round(mm / 1000, 12)
