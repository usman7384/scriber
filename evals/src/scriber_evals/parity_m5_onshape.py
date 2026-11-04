import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from scriber_agent import refine
from scriber_evals.parity import Demo, Evidence, Measured, Rig, evidence
from scriber_geometry.onshape import RecordedOnshape
from scriber_geometry.onshape_export import export_onshape
from scriber_ir import Design

ROOT = Path(__file__).parents[3]
FIXTURES = ROOT / "evals" / "parity" / "m5" / "onshape"
CHANGE = "Make the base plate 10 mm thick and open the motor bore to 24 mm"
# STEP upload (blob elements) and translation endpoints of the Onshape API
IMPORTS = ("/blobelements", "/translations", "/import")
NATIVE = {"assignVariable", "newSketch", "cPlane", "extrude", "hole"}


def motor_mount() -> Design:
    return Design.model_validate_json((FIXTURES / "motor_mount.json").read_text(encoding="utf-8"))


def ap_8(rig: Rig) -> Evidence:
    before, agent = motor_mount(), rig.config.agent
    r = list(refine(before, CHANGE, rig.llm, rig.geometry, rig.out / "refine", agent.max_repairs, agent.seed))[-1].result
    if not (r and r.design and r.artifact and r.artifact.ok):
        return evidence("AP-8", {"refined": False}, False)
    design, api = r.design, RecordedOnshape(FIXTURES)
    exported = export_onshape(api, design)
    sent = [body["feature"] for path, body in api.posts if path.endswith("/features")]
    (rig.out / "features.json").write_text(json.dumps(sent, indent=1), encoding="utf-8")
    old, new = before.param_values(), design.param_values()
    expr = {f["name"]: _quantities(f) for f in sent}
    part = design.parts[0]
    built = [(f.name, f.type) for f in exported.features if f.type in ("extrude", "hole")]
    sketches = [f.name for f in exported.features if f.type == "newSketch" and not f.name.endswith(" locations")]
    imports = [c for c in api.calls if any(i in c for i in IMPORTS)]
    m: Measured = {
        "changed": ", ".join(f"{k} {old[k]:g} to {new[k]:g}" for k in sorted(old) if new.get(k) != old[k]),
        "calls": len(api.calls),
        "endpoints": ", ".join(sorted({_endpoint(c) for c in api.calls})),
        "import_calls": len(imports),
        "features": ", ".join(f"{f.name} ({f.type})" for f in exported.features),
        "variables": ", ".join(f"{n}={expr[n]['lengthValue']}" for n in new),
        "linked": ", ".join(f"{n}.{k}={v}" for n, q in expr.items() for k, v in q.items() if v.startswith("#")),
        "dangling_refs": _dangling(sent, [f.feature_id for f in exported.features]),
        "volume_mm3": round(r.artifact.parts[0].volume, 3),
    }
    checks = [
        new == {**old, "plate_thickness": 10, "bore_diameter": 24},
        not imports and all(c.startswith("POST ") for c in api.calls),
        built == [(f.name, f.kind) for f in part.features] and sketches == [s.id for s in part.sketches],
        {f.type for f in exported.features} <= NATIVE and all(f.status == "OK" for f in exported.features),
        all(expr[p.name] == {"lengthValue": f"{p.value!r} mm"} for p in design.params),
        expr["Base plate"]["depth"] == "#plate_thickness" and expr["Motor bore"]["holeDiameter"] == "#bore_diameter",
        expr["bore plane"]["offset"] == "#plate_thickness + #boss_height",
        m["dangling_refs"] == 0 and _recorded(api) == [(f.name, f.type) for f in exported.features],
    ]
    note = "Onshape REST replayed from a recorded mock written from the public docs (no account, no network); bodies are the exporter's"
    return evidence("AP-8", m, *checks, note=note)


def _quantities(feature: dict[str, Any]) -> dict[str, str]:
    return {p["parameterId"]: p["expression"] for p in feature["parameters"] if "expression" in p}


def _endpoint(call: str) -> str:
    method, path = call.split(" ", 1)
    return f"{method} {path.split('/')[3]}" + ("/features" if path.endswith("/features") else "")


def _dangling(sent: list[dict[str, Any]], ids: list[str]) -> int:
    return sum(ref not in ids[:i] for i, f in enumerate(sent) for ref in _refs(f["parameters"]))


def _refs(params: list[dict[str, Any]]) -> Iterator[str]:
    return (q["featureId"] for p in params for q in p.get("queries", []) if "featureId" in q)


def _recorded(api: RecordedOnshape) -> list[tuple[str, str]]:
    replies = next(r for r in api.routes.values() if isinstance(r, list))
    features = [json.loads((api.root / f).read_text(encoding="utf-8"))["feature"] for f in replies]
    return [(f["name"], f["featureType"]) for f in features]


ROWS: dict[str, Demo] = {"AP-8": ap_8}
