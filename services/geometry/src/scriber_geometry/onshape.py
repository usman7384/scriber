import json
import re
from pathlib import Path
from typing import Any, Protocol

from scriber_geometry.models import Frozen
from scriber_ir import Design, Param, Provenance
from scriber_ir.model import Circle, Extrude, Part, PlaneRef, Polygon, Sketch

API = "/api/v10"
# deterministic ids of the default planes in every part studio
PLANES = {"JDC": "XY", "JCC": "XZ", "JEC": "YZ"}
TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}
QUANTITY = re.compile(r"^\s*([-+]?\d*\.?\d+)\s*([a-z]+)\s*$")


class OnshapeApi(Protocol):
    def get(self, path: str) -> bytes: ...

    def post(self, path: str, body: dict[str, Any]) -> bytes: ...


class OnshapeRef(Frozen):
    document: str
    workspace: str
    element: str


class ImportedFeature(Frozen):
    feature_id: str
    name: str
    type: str
    suppressed: bool
    mapped_to: str | None


class OnshapeImport(Frozen):
    bodies: list[str]
    features: list[ImportedFeature]
    design: Design
    step: Path


class RecordedOnshape:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.routes: dict[str, str | list[str]] = json.loads((root / "recording.json").read_text(encoding="utf-8"))
        self.calls: list[str] = []
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def get(self, path: str) -> bytes:
        return self._reply(f"GET {path}")

    def post(self, path: str, body: dict[str, Any]) -> bytes:
        self.posts.append((path, body))
        return self._reply(f"POST {path}")

    def _reply(self, key: str) -> bytes:
        self.calls.append(key)
        if key not in self.routes:
            raise KeyError(f"no recorded response for {key}")
        route, n = self.routes[key], self.calls.count(key)
        # a list holds the recorded replies to successive identical calls
        if isinstance(route, list) and n > len(route):
            raise KeyError(f"only {len(route)} recorded responses for {key}")
        return (self.root / (route if isinstance(route, str) else route[n - 1])).read_bytes()


def import_onshape(api: OnshapeApi, ref: OnshapeRef, step: Path) -> OnshapeImport:
    studio = f"{API}/partstudios/d/{ref.document}/w/{ref.workspace}/e/{ref.element}"
    features = json.loads(api.get(f"{studio}/features"))["features"]
    parts = json.loads(api.get(f"{API}/parts/d/{ref.document}/w/{ref.workspace}/e/{ref.element}"))
    step.write_bytes(_translate(api, ref, studio))
    design, imported = _design(ref, features, parts)
    return OnshapeImport(bodies=[p["name"] for p in parts], features=imported, design=design, step=step)


def _translate(api: OnshapeApi, ref: OnshapeRef, studio: str) -> bytes:
    request = {"formatName": "STEP", "stepVersionString": "AP242", "storeInDocument": False}
    job = json.loads(api.post(f"{studio}/translations", request))
    status = json.loads(api.get(f"{API}/translations/{job['id']}"))
    if status["requestState"] != "DONE":
        raise RuntimeError(f"STEP translation is {status['requestState']}; poll until DONE")
    return api.get(f"{API}/documents/d/{ref.document}/externaldata/{status['resultExternalDataIds'][0]}")


def _design(ref: OnshapeRef, features: list[dict[str, Any]], parts: list[dict[str, Any]]) -> tuple[Design, list[ImportedFeature]]:
    sketches: dict[str, Sketch] = {}
    built: list[dict[str, Any]] = []
    params: list[Param] = []
    imported = []
    for f in features:
        mapped = None if f.get("suppressed") else _map(ref, f, sketches, built, params, parts)
        imported.append(
            ImportedFeature(
                feature_id=f["featureId"], name=f["name"], type=f["featureType"], suppressed=bool(f.get("suppressed")), mapped_to=mapped
            )
        )
    design = Design(title=f"Onshape part studio {ref.element}"[:60], params=params, parts=[Part.model_validate(p) for p in built])
    return design, imported


def _map(
    ref: OnshapeRef,
    f: dict[str, Any],
    sketches: dict[str, Sketch],
    built: list[dict[str, Any]],
    params: list[Param],
    parts: list[dict[str, Any]],
) -> str | None:
    fid, args = _snake(f["name"]), {p["parameterId"]: p for p in f["parameters"]}
    if f["featureType"] == "newSketch":
        plane = PLANES.get(args["sketchPlane"]["queries"][0]["deterministicIds"][0])
        if plane is not None:
            sketches[f["featureId"]] = Sketch(id=fid, plane=PlaneRef(ref=plane), entities=_entities(f["entities"]))
        return fid if plane else None
    if f["featureType"] != "extrude" or args["bodyType"]["value"] != "SOLID":
        return None
    operation, bound = args["operationType"]["value"], args["endBound"]["value"]
    if bound not in ("BLIND", "THROUGH_ALL") or operation not in ("NEW", "ADD", "REMOVE") or (operation != "NEW" and not built):
        return None
    if operation == "NEW":
        source = parts[len(built)]
        material = source.get("material", {}).get("displayName")
        built.append({"id": _snake(source["name"]), "name": source["name"], "material": material, "sketches": [], "features": []})
    distance = _depth(ref, f, fid, params) if bound == "BLIND" else None
    sketch = sketches[args["entities"]["queries"][0]["featureId"]]
    mode = "cut" if operation == "REMOVE" else "add"
    extent = "blind" if distance else "through_all"
    built[-1]["sketches"].append(sketch)
    built[-1]["features"].append(
        Extrude(kind="extrude", id=fid, name=f["name"], sketch=sketch.id, mode=mode, extent=extent, distance=distance)
    )
    return fid


def _depth(ref: OnshapeRef, f: dict[str, Any], fid: str, params: list[Param]) -> str:
    depth = next(p["expression"] for p in f["parameters"] if p["parameterId"] == "depth")
    cite = Provenance(source="document", ref=f"onshape:{ref.document}/{ref.element}#{f['featureId']}.depth", quote=depth)
    params.append(Param(name=f"{fid}_depth", value=_mm(depth), unit="mm", provenance=cite))
    return f"{fid}_depth"


def _entities(entities: list[dict[str, Any]]) -> list[Circle | Polygon]:
    circles = [e["geometry"] for e in entities if e["geometry"]["btType"].startswith("BTCurveGeometryCircle")]
    lines = [_segment(e) for e in entities if e["geometry"]["btType"].startswith("BTCurveGeometryLine")]
    shapes: list[Circle | Polygon] = [Polygon(kind="polygon", points=loop) for loop in _loops(lines)]
    for c in circles:
        center = (_m(c["xCenter"]), _m(c["yCenter"]))
        shapes.append(Circle(kind="circle", center=center, diameter=_m(2 * c["radius"])))
    return shapes


def _segment(e: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]]:
    g = e["geometry"]
    x, y, dx, dy = g["pntX"], g["pntY"], g["dirX"], g["dirY"]
    return (_m(x + dx * e["startParam"]), _m(y + dy * e["startParam"])), (_m(x + dx * e["endParam"]), _m(y + dy * e["endParam"]))


def _loops(lines: list[tuple[tuple[float, float], tuple[float, float]]]) -> list[list[tuple[float | str, float | str]]]:
    loops: list[list[tuple[float | str, float | str]]] = []
    left = list(lines)
    while left:
        start, end = left.pop(0)
        loop: list[tuple[float | str, float | str]] = [start]
        while end != start:
            nxt = next((s for s in left if end in s), None)
            if nxt is None:
                raise ValueError(f"sketch profile is open at {end}")
            left.remove(nxt)
            loop.append(end)
            end = nxt[1] if nxt[0] == end else nxt[0]
        loops.append(loop)
    return loops


def _mm(quantity: str) -> float:
    match = QUANTITY.match(quantity)
    if not match or match.group(2) not in TO_MM:
        raise ValueError(f"unsupported quantity {quantity!r}")
    return round(float(match.group(1)) * TO_MM[match.group(2)], 9)


def _m(metres: float) -> float:
    return round(metres * 1000, 9)


def _snake(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
