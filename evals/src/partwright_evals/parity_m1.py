import json
import re
import struct
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from partwright_agent import check, generate, refine
from partwright_cli.store import params_table
from partwright_evals.parity import Demo, Evidence, Measured, Rig, evidence
from partwright_evals.run import load_cases
from partwright_geometry import Artifact, BuildError
from partwright_ir import Design, apply_params, compile_design, design_hash

FIXTURES = Path(__file__).parents[2] / "parity" / "m1"
CASES = Path(__file__).parents[2] / "cases" / "m1.yaml"
VALIDATOR = Path(__file__).parents[2] / "parity" / "tools" / "validate_gltf.mjs"
ANGLED = re.compile(r"gusset|rib|brace|support|strut|angle", re.IGNORECASE)
CYLINDER = "Hollow cylinder, 50mm height, 2mm wall thickness"
BRACKET = "mounting bracket, 4x M6 holes, 80x60 plate, 5 mm thick"


def fixture(name: str) -> Design:
    return Design.model_validate_json((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def build(rig: Rig, design: Design, name: str = "build") -> Artifact:
    return rig.geometry.build(design, rig.out / name)


def last_result(rig: Rig, prompt: str, name: str) -> tuple[Design | None, Artifact | None]:
    steps = list(generate(prompt, rig.llm, rig.geometry, rig.out / name, rig.config.agent.max_repairs, rig.config.agent.seed))
    r = steps[-1].result
    return (r.design, r.artifact) if r else (None, None)


def in_1(rig: Rig) -> Evidence:
    design, art = last_result(rig, CYLINDER, "cylinder")
    if not (design and art):
        return evidence("IN-1", {"built": False}, False)
    (part,) = art.parts
    bores = [h.diameter for h in part.holes]
    od, height = max(part.bbox_size[:2]), part.bbox_size[2]
    wall = (od - max(bores)) / 2 if bores else None
    m: Measured = {
        "solids": part.solids,
        "valid": part.valid,
        "height": round(height, 3),
        "od": round(od, 3),
        "wall": wall and round(wall, 3),
    }
    return evidence("IN-1", m, part.solids == 1, part.valid, abs(height - 50) <= 0.1, wall is not None and abs(wall - 2) <= 0.05)


def dp_5(rig: Rig) -> Evidence:
    return in_1(rig).model_copy(update={"row": "DP-5"})


def ge_1(rig: Rig) -> Evidence:
    first, second = build(rig, fixture("glider"), "a"), build(rig, fixture("glider"), "b")
    step = first.files["step"].read_text(encoding="utf-8", errors="replace")
    meshes = sum(step.count(e) for e in ("TRIANGULATED_FACE", "TESSELLATED_SHELL", "TESSELLATED_SOLID"))
    reloaded = rig.geometry.import_step(first.files["step"])
    drift = max(abs(a.volume - b.volume) for a, b in zip(first.parts, second.parts, strict=True))
    breps, valid = step.count("MANIFOLD_SOLID_BREP"), all(p.valid for p in reloaded)
    m: Measured = {"brep_solids": breps, "mesh_entities": meshes, "valid": valid, "volume_drift": drift}
    return evidence("GE-1", m, breps == 3, meshes == 0, valid, drift <= 1e-6)


def ge_2(rig: Rig) -> Evidence:
    design = fixture("glider")
    art = build(rig, design)
    deterministic = compile_design(design) == compile_design(fixture("glider")) == art.files["py"].read_text(encoding="utf-8")
    persisted = art.files["ir"].exists() and Design.model_validate_json(art.files["ir"].read_text(encoding="utf-8")) == design
    broken = _misplaced_hole(design)
    try:
        build(rig, broken, "broken")
        named = None
    except BuildError as e:
        named = e.feature
    features = [f"{p.id}.{f.id}" for p in design.parts for f in p.features]
    m: Measured = {"persisted": persisted, "deterministic": deterministic, "error_feature": named, "features": ", ".join(features)}
    return evidence("GE-2", m, persisted, deterministic, named == "bad_hole", len(features) == 3)


def _misplaced_hole(design: Design) -> Design:
    data = design.model_dump(mode="json")
    hole = {
        "kind": "hole",
        "id": "bad_hole",
        "name": "Hole off the part",
        "plane": {"offset": 0},
        "at": {"kind": "points", "points": [[2000, 0]]},
    }
    data["parts"][2]["features"].append({**hole, "diameter": 5})
    return Design.model_validate(data)


def ge_7(rig: Rig) -> Evidence:
    runs = [last_result(rig, BRACKET, f"run{i}") for i in range(5)]
    hashes = {design_hash(d) if d else "none" for d, _ in runs}
    volumes = {round(sum(p.volume for p in a.parts), 6) if a else None for _, a in runs}
    m: Measured = {"runs": 5, "distinct_ir": len(hashes), "distinct_volumes": len(volumes), "volume": next(iter(volumes))}
    return evidence("GE-7", m, len(hashes) == 1, "none" not in hashes, len(volumes) == 1)


def ge_10(rig: Rig) -> Evidence:
    titles = [d.title if d else "" for d, _ in (last_result(rig, p, f"g{i}") for i, p in enumerate((CYLINDER, BRACKET)))]
    return evidence("GE-10", {"titles": " | ".join(titles)}, *(0 < len(t) <= 60 for t in titles))


def pr_1(rig: Rig) -> Evidence:
    rows = params_table(fixture("glider"))
    keys = {"name", "value", "unit", "min", "max", "provenance"}
    complete = all(keys <= r.keys() and r["unit"] for r in rows)
    (rig.out / "params.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return evidence(
        "PR-1", {"params": len(rows), "fields": ", ".join(sorted(keys))}, complete, note="API half; the panel is WP rows in the web suite"
    )


def pr_4(rig: Rig) -> Evidence:
    design = fixture("glider")
    steps = list(refine(design, "Increase length to 450 mm", rig.llm, rig.geometry, rig.out / "refine", rig.config.agent.max_repairs))
    r = steps[-1].result
    if not (r and r.design and r.artifact):
        return evidence("PR-4", {"built": False}, False)
    before, after = design.param_values(), r.design.param_values()
    changed = sorted(k for k in before if after.get(k) != before[k])
    m: Measured = {"length": after.get("length"), "changed": ", ".join(changed), "parts": len(r.design.parts), "valid": r.artifact.ok}
    return evidence(
        "PR-4", m, abs(after.get("length", 0) - 450) <= 0.01, changed == ["length"], r.design.parts == design.parts, r.artifact.ok
    )


def vm_6(rig: Rig) -> Evidence:
    art = build(rig, fixture("glider"))
    mesh = trimesh.load_mesh(art.files["stl"])
    _, uses = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    valid, solids, boundary = all(p.valid for p in art.parts), sum(p.solids for p in art.parts), int(np.sum(uses == 1))
    m: Measured = {"valid": valid, "solids": solids, "boundary_edges": boundary}
    return evidence("VM-6", m, valid, solids == 3, boundary == 0, bool(mesh.is_watertight))


def ex_1(rig: Rig) -> Evidence:
    art = build(rig, fixture("glider"))
    reloaded = rig.geometry.import_step(art.files["step"])
    drift = max(abs(a.volume - b.volume) for a, b in zip(art.parts, reloaded, strict=True))
    schema = "AP214" if "AUTOMOTIVE_DESIGN" in art.files["step"].read_text(encoding="utf-8", errors="replace") else "other"
    solids = sum(p.solids for p in reloaded)
    m: Measured = {"schema": schema, "solids": solids, "volume_drift": drift}
    return evidence("EX-1", m, schema == "AP214", solids == 3, drift <= 1e-6)


def ex_2(rig: Rig) -> Evidence:
    tube = Design.model_validate_json((FIXTURES / "tube.json").read_text(encoding="utf-8"))
    art = build(rig, tube)
    mesh = trimesh.load_mesh(art.files["stl"])
    deviation = _cylinder_chord_error(mesh, (27.0, 25.0))
    m: Measured = {"watertight": bool(mesh.is_watertight), "chordal_deviation_mm": round(deviation, 5), "triangles": len(mesh.faces)}
    return evidence("EX-2", m, bool(mesh.is_watertight), deviation <= 0.05)


def _cylinder_chord_error(mesh: trimesh.Trimesh, radii: tuple[float, ...]) -> float:
    corners = np.hypot(mesh.vertices[mesh.faces][:, :, 0], mesh.vertices[mesh.faces][:, :, 1])
    worst = 0.0
    for r in radii:
        on_wall = np.all(np.abs(corners - r) < 1e-3, axis=1)
        mids = (mesh.vertices[mesh.faces[on_wall]][:, [0, 1, 2]] + mesh.vertices[mesh.faces[on_wall]][:, [1, 2, 0]]) / 2
        worst = max(worst, float(np.max(np.abs(np.hypot(mids[..., 0], mids[..., 1]) - r))))
    return worst


def ex_3(rig: Rig) -> Evidence:
    art = build(rig, fixture("glider"))
    report = json.loads(subprocess.run(["node", str(VALIDATOR), str(art.files["glb"])], capture_output=True, text=True, check=True).stdout)
    (rig.out / "validator.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    names = sorted(str(n.get("name", "")) for n in _gltf_json(art.files["glb"])["nodes"] if "mesh" in n)
    errors = int(report["issues"]["numErrors"])
    m: Measured = {"errors": errors, "warnings": report["issues"]["numWarnings"], "mesh_nodes": ", ".join(names)}
    return evidence("EX-3", m, errors == 0, names == ["Fuselage", "Tailplane", "Wing"])


def _gltf_json(glb: Path) -> dict[str, Any]:
    data = glb.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    doc: dict[str, Any] = json.loads(data[20 : 20 + length])
    return doc


def _case(rig: Rig, row: str, case_id: str) -> tuple[Evidence, Design | None]:
    (case,) = [c for c in load_cases(CASES) if c.id == case_id]
    design, art = last_result(rig, case.prompt, case.id)
    results = check(case.checks, art) if art else []
    passed = sum(c.passed for c in results)
    failed = "; ".join(f"{c.requirement.description}: {c.actual}" for c in results if not c.passed)
    m: Measured = {"checks": f"{passed}/{len(case.checks)}", "valid": bool(art and art.ok), "failed": failed}
    return evidence(row, m, bool(art and art.ok), passed == len(case.checks)), design


def dp_7(rig: Rig) -> Evidence:
    ev, design = _case(rig, "DP-7", "dp7-angled-bracket")
    angled = [f"{p.id}.{f.id}" for p in design.parts for f in p.features if ANGLED.search(f.name)] if design else []
    angled += _sloped_sketches(design) if design else []
    return ev.model_copy(update={"passed": ev.passed and bool(angled), "measured": {**ev.measured, "angled": ", ".join(angled)}})


def _sloped_sketches(design: Design) -> list[str]:
    found = []
    for part in design.parts:
        for sketch in part.sketches:
            for e in sketch.model_dump(mode="json")["entities"]:
                pts = e.get("points") or ([e["start"], *(s["to"] for s in e["segments"])] if e.get("kind") == "path" else [])
                if any(_sloped(a, b) for a, b in zip(pts, pts[1:] + pts[:1], strict=True)):
                    found.append(f"{part.id}.{sketch.id}")
    return found


def _sloped(a: list[object], b: list[object]) -> bool:
    if not all(isinstance(v, int | float) for v in (*a, *b)):
        return False
    dx, dy = float(b[0]) - float(a[0]), float(b[1]) - float(a[1])  # type: ignore[arg-type]
    return abs(dx) > 1e-6 and abs(dy) > 1e-6


def dp_21(rig: Rig) -> Evidence:
    return _case(rig, "DP-21", "dp21-l-bracket")[0]


def dp_2(rig: Rig) -> Evidence:
    ev, design = _case(rig, "DP-2", "dp2-flanged-adapter")
    if not (ev.passed and design):
        return ev
    spacing = [p.name for p in design.params if p.value == 85]
    if not spacing:
        return ev.model_copy(update={"passed": False, "note": "no parameter holds the 85 mm hole spacing"})
    edited = build(rig, apply_params(design, {spacing[0]: 90}), "edit-x-90")
    xs = sorted({round(h.center[0], 2) for p in edited.parts for h in p.holes if abs(h.diameter - 8.5) <= 0.05})
    moved = len(xs) == 2 and abs(xs[1] - xs[0] - 90) <= 0.05
    return ev.model_copy(
        update={"passed": edited.ok and moved, "measured": {**ev.measured, "edited_x_spacing": xs[1] - xs[0] if len(xs) == 2 else None}}
    )


ROWS: dict[str, Demo] = {
    "IN-1": in_1,
    "DP-5": dp_5,
    "GE-1": ge_1,
    "GE-2": ge_2,
    "GE-7": ge_7,
    "GE-10": ge_10,
    "PR-1": pr_1,
    "PR-4": pr_4,
    "VM-6": vm_6,
    "EX-1": ex_1,
    "EX-2": ex_2,
    "EX-3": ex_3,
    "DP-2": dp_2,
    "DP-7": dp_7,
    "DP-21": dp_21,
}
