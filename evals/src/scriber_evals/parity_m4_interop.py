import json
import math
import re
from pathlib import Path

from scriber_agent.prompts import EXAMPLES
from scriber_evals.parity import Demo, Evidence, Measured, Rig, Value, evidence
from scriber_evals.parity_m5_onshape import FIXTURES as ONSHAPE_EXPORT
from scriber_evals.parity_m5_onshape import IMPORTS, motor_mount
from scriber_evals.tools import FREECAD, missing, tool
from scriber_geometry import (
    PartMetrics,
    SketchDof,
    UnsupportedExportError,
    export_bundle,
    export_fcstd,
    fcstd_plan,
    inspect_fcstd,
    open_bundle,
    sketch_dof,
)
from scriber_geometry.onshape import OnshapeRef, RecordedOnshape, import_onshape
from scriber_geometry.onshape_export import export_onshape
from scriber_ir import Design, apply_params, design_hash, validate
from scriber_ir.model import Extrude

ROOT = Path(__file__).parents[3]
FIXTURES = ROOT / "evals" / "parity" / "m4" / "interop"
INTEROP_DOC = ROOT / "docs" / "INTEROP.md"
ONSHAPE = OnshapeRef(document="5f1c2a9e0b7d4e3a8c6f1b2d", workspace="8e4b7c1d2a3f4e5b6c7d8e9f", element="3a9d2c1b0e8f7a6b5c4d3e2f")
GEARBOX = ["gearbox/base_plate", "gearbox/shaft_assembly/shaft", "gearbox/shaft_assembly/bearing", "gearbox/cover"]
PROPRIETARY = ["CATIA", "NX", "SolidWorks", "Creo", "Inventor", "Parasolid"]
REFERENCE = ROOT / "evals" / "parity" / "m5" / "reference"
SKETCH = "Sketcher::SketchObject"


def bracket() -> Design:
    return Design.model_validate_json((FIXTURES / "bracket.json").read_text(encoding="utf-8"))


def ge_12(rig: Rig) -> Evidence:
    design = bracket()
    art = rig.geometry.build(design, rig.out / "bracket")
    meta = rig.geometry.step_metadata(art.files["step"])
    (body,) = meta.bodies
    groups = {g.name: g for g in body.face_groups}
    reopened = open_bundle(export_bundle(design, art.files["step"], rig.out / "bracket.zip")).design.parts[0]
    mount, load, bores = groups["mount_face"], groups["load_face"], groups["bolt_bores"]
    plate = 80 * 60 - (4 - math.pi) * 5**2 - 4 * math.pi * 3.3**2
    m: Measured = {
        "schema": meta.schema_name,
        "step_face_groups": ", ".join(groups),
        "material": body.material,
        "density_g_cm3": body.density_g_cm3,
        "mount_area": round(mount.area, 3),
        "mount_normal": str(mount.normal),
        "load_area": round(load.area, 3),
        "load_z": round(load.center[2], 6),
        "bolt_bore_faces": bores.faces,
        "bundle_face_groups": ", ".join(g.name for g in reopened.face_groups),
        "bundle_material": reopened.material,
    }
    checks = [
        meta.schema_name.startswith("AP242"),
        set(groups) == {"mount_face", "load_face", "bolt_bores"},
        body.material == "6061 aluminium" and body.density_g_cm3 == 2.7,
        abs(mount.area - plate) < 1e-3 and mount.normal == (0.0, 0.0, -1.0) and abs(mount.center[2]) < 1e-9,
        abs(load.area - math.pi * 100) < 1e-3 and load.normal == (0.0, 0.0, 1.0) and abs(load.center[2] - 21) < 1e-9,
        bores.faces == 4 and abs(bores.area - 4 * math.pi * 6.6 * 6) < 1e-3,
        [g.name for g in reopened.face_groups] == ["mount_face", "load_face", "bolt_bores"] and reopened.material == body.material,
    ]
    return evidence("GE-12", m, *checks, note="face names are STEP AP242 named sub-shapes; material is an AP214/AP242 material property")


def recorded_designs() -> dict[str, Design]:
    designs = {design_hash(d): d for d in (Design.model_validate(x) for _, x in EXAMPLES)}
    fixtures = (ROOT / "evals" / "parity").glob("m*/**/*.json")
    # a recorded design counts only if the kernel built it; failed attempts can hold degenerate sketches
    built = [p for p in (ROOT / "evals" / "results").rglob("design.json") if (p.parent / "model.step").exists()]
    for path in sorted([*built, *fixtures]):
        data = json.loads(path.read_text(encoding="utf-8"))
        # fixtures also hold assemblies of designs, answers and specs; only whole designs count
        if isinstance(data, dict) and {"title", "params", "parts"} <= data.keys():
            d = Design.model_validate(data)
            designs.setdefault(design_hash(d), d)
    return designs


def ge_3(rig: Rig) -> Evidence:
    designs = recorded_designs()
    reports = [r for d in designs.values() for r in sketch_dof(d)]
    bundle = open_bundle(
        export_bundle(bracket(), rig.geometry.build(bracket(), rig.out / "bracket").files["step"], rig.out / "bracket.zip")
    )
    constraints = [c for r in reports for c in r.constraints]
    m: Measured = {
        "designs": len(designs),
        "sketches": len(reports),
        "fully_constrained": sum(r.dof == 0 for r in reports),
        "unsupported": sum(r.dof is None for r in reports),
        "max_solve_error": max(r.solve_error for r in reports),
        "constraints": len(constraints),
        "driven_by_ir_expressions": sum(c.expr is not None for c in constraints),
        "plain_positions": sum(c.expr is None and c.kind.startswith("distance") and len(c.refs) == 1 for c in constraints),
        "bundle_sketches": ", ".join(f"{s.sketch}: {len(s.constraints)} constraints, dof {s.dof}" for s in bundle.sketches),
    }
    (rig.out / "sketches.json").write_text(json.dumps([r.model_dump() for r in reports], indent=1), encoding="utf-8")
    checks = [all(r.dof == 0 for r in reports), all(r.solve_error < 1e-6 for r in reports), _bundle_constrained(bundle.sketches)]
    return evidence(
        "GE-3",
        m,
        *checks,
        note="every IR design in the repo: worked examples, fixtures and live-run outputs; FreeCAD Sketcher replay not run",
    )


def _bundle_constrained(sketches: list[SketchDof]) -> bool:
    return bool(sketches) and all(s.dof == 0 and s.constraints for s in sketches)


def in_10(rig: Rig) -> Evidence:
    gearbox = rig.geometry.step_metadata(FIXTURES / "gearbox_ap242.step")
    solids = rig.geometry.import_step(FIXTURES / "gearbox_ap242.step")
    api = RecordedOnshape(FIXTURES / "onshape")
    imported = import_onshape(api, ONSHAPE, rig.out / "part_studio.step")
    listed = json.loads((FIXTURES / "onshape" / "features.json").read_text(encoding="utf-8"))["features"]
    built = rig.geometry.build(imported.design, rig.out / "onshape_ir")
    exported = {p.name: p.volume for p in rig.geometry.import_step(imported.step)}
    drift = (
        max(abs(p.volume - exported[p.name]) / exported[p.name] for p in built.parts)
        if set(exported) == {p.name for p in built.parts}
        else 1.0
    )
    ir_tree = [f.name for p in imported.design.parts for f in p.features]
    out_of_scope = _out_of_scope(INTEROP_DOC.read_text(encoding="utf-8"))
    m: Measured = {
        "step_schema": gearbox.schema_name,
        "step_bodies": ", ".join(b.path for b in gearbox.bodies),
        "onshape_features": ", ".join(f"{f.name} ({f.type})" for f in imported.features),
        "mapped": f"{sum(f.mapped_to is not None for f in imported.features)}/{len(imported.features)}",
        "ir_features": ", ".join(ir_tree),
        "onshape_bodies": ", ".join(imported.bodies),
        "body_volume_drift": drift,
        "docs_out_of_scope": ", ".join(out_of_scope),
    }
    checks = [
        gearbox.schema_name.startswith("AP242"),
        [b.path for b in gearbox.bodies] == GEARBOX and [p.name for p in solids] == [g.rsplit("/", 1)[1] for g in GEARBOX],
        all(p.valid for p in solids),
        [(f.feature_id, f.name, f.type) for f in imported.features] == [(f["featureId"], f["name"], f["featureType"]) for f in listed],
        ir_tree == [f["name"] for f in listed if f["featureType"] == "extrude"],
        [p.name for p in imported.design.parts] == imported.bodies == list(exported),
        validate(imported.design) == [] and drift < 1e-6,
        set(PROPRIETARY) <= set(out_of_scope),
    ]
    return evidence("IN-10", m, *checks, note="Onshape API replayed from a recorded mock (no account); STEP fixtures written by OCCT")


def _out_of_scope(doc: str) -> list[str]:
    section = doc.split("## Out of scope", 1)[1].split("\n## ", 1)[0] if "## Out of scope" in doc else ""
    return [name for name in PROPRIETARY if re.search(rf"\b{name}\b", section)]


def ex_4(rig: Rig) -> Evidence:
    design = bracket()
    art = rig.geometry.build(design, rig.out / "bracket")
    bundle = open_bundle(export_bundle(design, art.files["step"], rig.out / "bracket.zip"))
    rebuilt = rig.geometry.build(bundle.design, rig.out / "reopened")
    bundle_ok = (
        [f.name for f in bundle.features] == [f.name for f in design.parts[0].features]
        and _bundle_constrained(bundle.sketches)
        and abs(rebuilt.parts[0].volume - art.parts[0].volume) < 1e-6
    )
    onshape, onshape_ok = _onshape_export()
    supported, unsupported = _fcstd_coverage(rig)
    freecad = tool(FREECAD)
    m: dict[str, Value] = {
        "bundle_files": ", ".join(sorted(bundle.files)),
        "features": ", ".join(f"{f.name} <- {', '.join(f.depends_on)}" for f in bundle.features),
        "sketch_constraints": ", ".join(f"{s.sketch}: {len(s.constraints)}" for s in bundle.sketches),
        "sketch_dof": ", ".join(f"{s.sketch}: {s.dof}" for s in bundle.sketches),
        "volume_drift": abs(rebuilt.parts[0].volume - art.parts[0].volume),
        "bundle_ok": bundle_ok,
        "onshape_features": onshape,
        "onshape_ok": onshape_ok,
        "fcstd_reference_designs": f"{len(supported)}/{len(supported) + len(unsupported)} map to PartDesign",
        "fcstd_unsupported": "; ".join(f"{k}: {v}" for k, v in unsupported.items()),
        "freecad": str(freecad) if freecad else missing(FREECAD),
    }
    fcstd = [_fcstd(rig, name, part, freecad) for name, part in (("bracket", design), ("flange", flange()))] if freecad else []
    for found, _ in fcstd:
        m |= found
    m["fcstd_ok"] = fcstd_ok = bool(fcstd) and all(ok for _, ok in fcstd)
    note = (
        "FCStd written and reopened by FreeCAD 1.1.4 (freecadcmd); Onshape half = native feature export (AP-8 exporter) "
        "against the recorded mock, not FeatureScript source"
    )
    return evidence("EX-4", m, bundle_ok, onshape_ok, fcstd_ok, note=note)


def flange() -> Design:
    return Design.model_validate_json((ROOT / "evals" / "parity" / "m4" / "mesh" / "flange.json").read_text(encoding="utf-8"))


def _onshape_export() -> tuple[str, bool]:
    api, design = RecordedOnshape(ONSHAPE_EXPORT), motor_mount()
    exported = export_onshape(api, design)
    built = [(f.name, f.type) for f in exported.features if f.type in ("extrude", "hole")]
    ok = (
        built == [(f.name, f.kind) for f in design.parts[0].features]
        and all(f.status == "OK" for f in exported.features)
        and not any(i in c for c in api.calls for i in IMPORTS)
    )
    return ", ".join(f"{f.name} ({f.type})" for f in exported.features if f.type != "assignVariable"), ok


def _fcstd_coverage(rig: Rig) -> tuple[list[str], dict[str, str]]:
    supported, unsupported = [], {}
    for path in sorted(REFERENCE.glob("b*.json")):
        design = Design.model_validate_json(path.read_text(encoding="utf-8"))
        try:
            fcstd_plan(design, rig.geometry.frames(design))
            supported.append(path.stem)
        except UnsupportedExportError as e:
            unsupported[path.stem] = str(e)
    return supported, unsupported


def _fcstd(rig: Rig, name: str, design: Design, freecad: Path) -> tuple[dict[str, Value], bool]:
    [ours] = rig.geometry.build(design, rig.out / f"{name}_ours").parts
    path = export_fcstd(design, rig.geometry.frames(design), freecad, rig.out / f"{name}.FCStd")
    edits = {p.name: round(p.value * 1.05, 6) for p in design.params if p.unit == "mm"}
    report = inspect_fcstd(freecad, path, edits, rig.out / f"{name}_edits")
    [body] = report.bodies
    sketches = [f for f in body.features if f.type == SKETCH]
    expected = [x for f in design.parts[0].features for x in (f.sketch if isinstance(f, Extrude) else f"{f.id}_centres", f.name)]
    drift = abs(body.volume - ours.volume) / ours.volume
    followed = [
        k for k, v in edits.items() if _same(rig.geometry.import_step(report.edited[k]), rig.geometry.measure(apply_params(design, {k: v})))
    ]
    m: dict[str, Value] = {
        f"{name}_tree": ", ".join(f"{f.label} ({f.type.split('::')[1]})" for f in body.features),
        f"{name}_sketches": ", ".join(f"{s.label}: {s.constraints} constraints, dof {s.dof}" for s in sketches),
        f"{name}_redundant_or_conflicting": sum((s.redundant or 0) + (s.conflicting or 0) for s in sketches),
        f"{name}_expressions": sum(f.expressions for f in body.features),
        f"{name}_recompute_errors": "; ".join(report.errors),
        f"{name}_volume_drift": drift,
        f"{name}_params_driving_the_model": f"{len(followed)}/{len(edits)}",
    }
    ok = (
        [f.label for f in body.features] == expected
        and all(s.dof == 0 and s.constraints and not s.redundant and not s.conflicting for s in sketches)
        and not report.errors
        and body.valid
        and body.solids == 1
        and drift <= 1e-3
        and len(followed) == len(edits)
    )
    return m, ok


def _same(theirs: list[PartMetrics], ours: list[PartMetrics]) -> bool:
    # an edit is followed when FreeCAD's recomputed body matches our rebuild: volume, centre of mass and every hole
    [a], [b] = theirs, ours
    if a.center_of_mass is None or b.center_of_mass is None or len(a.holes) != len(b.holes):
        return False
    com = max(abs(x - y) for x, y in zip(a.center_of_mass, b.center_of_mass, strict=True))
    holes = all(any(abs(h.diameter - k.diameter) < 1e-6 and math.dist(h.center, k.center) < 1e-6 for k in a.holes) for h in b.holes)
    return abs(a.volume - b.volume) / b.volume < 1e-6 and com < 1e-6 and holes


ROWS: dict[str, Demo] = {"GE-12": ge_12, "GE-3": ge_3, "IN-10": in_10, "EX-4": ex_4}
