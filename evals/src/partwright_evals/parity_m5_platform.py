import base64
import importlib.util
import json
import math
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import numpy.typing as npt
import trimesh

from partwright_cli.pipe import pipe
from partwright_context import HashEmbedder, LocalContext, archive_files, ingest_all
from partwright_context.sizing import XmlSizing
from partwright_evals.legacy_archive import BROKEN_PDF, BROKEN_STEP, make_archive
from partwright_evals.parity import Demo, Evidence, Measured, Rig, evidence
from partwright_evals.parity_api import NO_REQS, Api, Response, Seeded, serve
from partwright_evals.parity_m4_aircraft import wing_checks
from partwright_geometry import Artifact
from partwright_ir import Design, material

ROOT = Path(__file__).parents[3]
FIXTURES = ROOT / "evals" / "parity" / "m5" / "platform"
SIZING = ROOT / "evals" / "parity" / "m4" / "aircraft" / "sizing.xml"
SKETCH_PNG = ROOT / "evals" / "parity" / "m3" / "sketch.png"
INTEROP_DOC = ROOT / "docs" / "INTEROP.md"
EXAMPLES_DOC = ROOT / "docs" / "EXAMPLES.md"
FREECAD = ("FreeCADCmd", "freecadcmd", "freecad")
Array = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Recorded:
    api: Api

    def post(
        self,
        url: str,
        *,
        json: Any = None,
        params: dict[str, str] | None = None,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        sent = {"json": json, "params": params, "content": content, "headers": headers}
        return self.api.call("POST", url, **{k: v for k, v in sent.items() if v is not None})

    def get(self, url: str) -> Response:
        return self.api.call("GET", url)


def fixture(name: str) -> dict[str, Any]:
    found: dict[str, Any] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return found


def example(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "examples" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(api: Api, project: str, design: dict[str, Any], prompt: str | None = None) -> dict[str, Any]:
    return api.wait(api.ok("POST", f"/projects/{project}/designs", json={"design": design, "prompt": prompt})["id"])


def download(api: Api, job: dict[str, Any], fmt: str, path: Path) -> Path:
    path.write_bytes(api.call("GET", f"/models/{job['model_id']}/export", params={"fmt": fmt, "version": job["version"]}).content)
    return path


def loops(stl: Path, origin: tuple[float, float, float], normal: tuple[float, float, float]) -> list[Array]:
    section = trimesh.load_mesh(stl).section(plane_origin=origin, plane_normal=normal)
    if section is None:
        raise ValueError(f"{stl.name}: the plane through {origin} misses the mesh")
    return [np.asarray(p, dtype=np.float64) for p in section.discrete]


def ring_area(points: Array) -> float:
    x, y = points[:, 0], points[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def outline_distances(points: Array, outline: list[tuple[float, float]]) -> Array:
    poly = np.asarray(outline + outline[:1], dtype=np.float64)
    a, b = poly[:-1], poly[1:]
    ab = b - a
    t = np.clip(((points[:, None, :] - a) * ab).sum(-1) / (ab**2).sum(-1), 0, 1)
    nearest = a + t[..., None] * ab
    distances: Array = np.linalg.norm(points[:, None, :] - nearest, axis=-1).min(axis=1)
    return distances


def ap_6(rig: Rig) -> Evidence:
    box = example("shadow_box")
    tool = rig.geometry.build(Design.model_validate(fixture("tool.json")), rig.out / "tool").files["stl"]
    outline, height = box.tool_outline(tool)
    with serve(rig, Seeded([])) as api:
        job = box.submit(Recorded(api), api.project("Shadow box"), box.insert_design(outline, height, 1.0), "shadow box for tool.stl")
        stl = download(api, job, "stl", rig.out / "insert.stl")
        version = api.version(job["model_id"])
    depth = {p["name"]: p["value"] for p in version["params"]}
    z = depth["floor"] + depth["pocket_depth"] / 2
    pocket = min(loops(stl, (0, 0, z), (0, 0, 1)), key=ring_area)[:, :2]
    samples = np.vstack([pocket, (pocket + np.roll(pocket, -1, axis=0)) / 2])
    gaps = outline_distances(samples, outline)
    m: Measured = {
        "tool_vertices": len(outline),
        "tool_thickness": round(height, 4),
        "pocket_samples": len(samples),
        "offset_min": round(float(gaps.min()), 4),
        "offset_max": round(float(gaps.max()), 4),
        "job": job["status"],
        "documented": EXAMPLES_DOC.exists() and "shadow_box.py" in EXAMPLES_DOC.read_text(encoding="utf-8"),
    }
    checks = (job["status"] == "done", bool(abs(gaps.min() - 1) <= 0.05), bool(abs(gaps.max() - 1) <= 0.05), bool(m["documented"]))
    note = "pocket section at half depth of the exported STL, vertices and chord midpoints, distance to the tool's mid-height outline"
    return evidence("AP-6", m, *checks, note=note)


def dp_19(rig: Rig) -> Evidence:
    holder = example("phone_holder")
    with serve(rig, Seeded([])) as api:
        job = holder.submit(Recorded(api), api.project("Phone holder"), 75.0)
        stl = download(api, job, "stl", rig.out / "phone_holder.stl")
        params = {p["name"]: p for p in api.version(job["model_id"])["params"]}
    z = params["base"]["value"] + params["lip_height"]["value"] / 2
    (profile,) = loops(stl, (0, 0, 0), (0, 1, 0))
    xs = sorted(_crossings(profile[:, [0, 2]], z))
    inner = xs[2] - xs[1] if len(xs) == 4 else float("nan")
    m: Measured = {
        "phone_width": params["phone_width"]["value"],
        "source": params["phone_width"]["provenance"]["quote"],
        "inner_width": round(inner, 4),
        "expected": 75.5,
        "job": job["status"],
    }
    return evidence(
        "DP-19", m, job["status"] == "done", abs(inner - 75.5) <= 0.05, note="cut across the cradle at mid-depth, mid-lip height"
    )


def _crossings(ring: Array, z: float) -> list[float]:
    out = []
    for (x0, z0), (x1, z1) in zip(ring, np.roll(ring, -1, axis=0), strict=True):
        if min(z0, z1) <= z < max(z0, z1):
            out.append(float(x0 + (z - z0) * (x1 - x0) / (z1 - z0)))
    return out


def ap_9(rig: Rig) -> Evidence:
    llm = Seeded([])
    with serve(rig, llm) as api:
        job = pipe(SIZING.read_bytes(), Recorded(api), None, SIZING.name)
        step = download(api, job, "step", rig.out / "wing.step")
        version = api.version(job["model_id"])
    art = Artifact(design_hash="", files={"step": step}, parts=rig.geometry.import_step(step), findings=[], elapsed_ms=0)
    m, checks = wing_checks(rig, XmlSizing().read(SIZING), art)
    m = {**m, "origin": version["origin"], "llm_calls": llm.calls, "job": job["status"]}
    note = "partwright_cli.pipe.pipe (the `partwright pipe` command) against the in-process API; IN-11 checks on the downloaded STEP"
    return evidence("AP-9", m, *checks, job["status"] == "done", llm.calls == 0, note=note)


def wp_11(rig: Rig) -> Evidence:
    shot = SKETCH_PNG.read_bytes()
    with serve(rig, Seeded([])) as api:
        job = build(api, api.project(), fixture("plate.json"))
        body = {"model_id": job["model_id"], "version": job["version"], "text": "the left hole is off by 2 mm"}
        bug = api.ok("POST", "/bugs", json={**body, "screenshot": "data:image/png;base64," + base64.b64encode(shot).decode()})
        [stored] = api.ok("GET", "/bugs", params={"model_id": job["model_id"]})
        image = api.call("GET", stored["screenshot_url"]).content
    m: Measured = {k: stored[k] for k in ("model_id", "version", "text", "user")}
    m = {**m, "screenshot_bytes": len(image), "screenshot_matches": image == shot}
    same = all(stored[k] == body[k] for k in body) and stored["id"] == bug["id"]
    note = "API half: the web dialog posts this shape (apps/web BugReport); no end-to-end browser run against the live API"
    return evidence("WP-11", m, same, image == shot, note=note)


def wp_12(rig: Rig) -> Evidence:
    limit = 3
    with serve(rig, Seeded(_plates(limit + 1)), auth="tokens", generation_limit=limit) as api:
        alice, bob = _users(api, "alice", "bob")
        project = api.ok("POST", "/projects", json={"name": "Quota"}, headers=alice)["id"]
        codes = [_generate(api, project, alice) for _ in range(limit + 1)]
        other = _generate(api, project, bob)
        usage = api.ok("GET", "/usage", headers=alice)
    with serve(rig, Seeded(_plates(11)), data=rig.out / "unlimited") as api:
        project = api.project()
        batch = api.ok("POST", "/batch", json={"project_id": project, "prompts": [f"plate {i}" for i in range(11)]})
        unlimited = [api.wait(j["id"])["status"] for j in batch["jobs"]]
        default = api.ok("GET", "/usage")
    m: Measured = {
        "limit": limit,
        "alice_codes": ", ".join(map(str, codes)),
        "bob_code": other,
        "alice_usage": usage["generations"],
        "default_limit": default["limit"],
        "default_generations": default["generations"],
        "default_done": unlimited.count("done"),
    }
    checks = (codes == [202] * limit + [429], other == 202, default["limit"] is None, unlimited.count("done") == 11)
    return evidence("WP-12", m, *checks, note="a user is the token's name; 11 > the reference's 10 free generations with no limit set")


def _plates(n: int) -> list[str]:
    return [a for _ in range(n) for a in (NO_REQS, json.dumps(fixture("plate.json")))]


def _users(api: Api, *names: str) -> list[dict[str, str]]:
    first = api.ok("POST", "/tokens", json={"name": names[0]})["token"]
    rest = [api.ok("POST", "/tokens", json={"name": n}, headers={"X-API-Token": first})["token"] for n in names[1:]]
    api.client.headers.update({"X-API-Token": first})
    return [{"X-API-Token": t} for t in (first, *rest)]


def _generate(api: Api, project: str, headers: dict[str, str]) -> int:
    response = api.call("POST", f"/projects/{project}/generate", json={"prompt": "Mounting plate 120 x 80 x 5 mm"}, headers=headers)
    if response.is_success:
        api.wait(response.json()["id"])
    return response.status_code


def wp_10(rig: Rig) -> Evidence:
    with serve(rig, Seeded([]), auth="tokens") as api:
        alice, bob = _users(api, "alice", "bob")
        original = build(api, api.ok("POST", "/projects", json={"name": "Alice"}, headers=alice)["id"], fixture("plate.json"))
        published = api.ok("POST", "/community", json={"model_id": original["model_id"]}, headers=alice)
        seen = [p["id"] for p in api.ok("GET", "/community", headers=bob)]
        mine = api.ok("POST", "/projects", json={"name": "Bob"}, headers=bob)["id"]
        fork = api.ok("POST", f"/community/{published['id']}/fork", json={"project_id": mine}, headers=bob)
        edit = api.wait(api.ok("PATCH", f"/models/{fork['id']}/params", json={"values": {"thickness": 8}}, headers=bob)["id"])
        forked = api.ok("GET", f"/models/{fork['id']}", headers=bob)
        kept = api.ok("GET", f"/models/{original['model_id']}", headers=alice)
    source = fork["forked_from"] or {}
    m: Measured = {
        "author": published["author"],
        "visible_to_bob": published["id"] in seen,
        "fork_project": fork["project_id"] == mine,
        "forked_from": f"{source.get('model_id')} v{source.get('version')} by {source.get('author')}",
        "fork_versions": forked["versions"],
        "fork_thickness": forked["version"]["metrics"]["bbox"][2],
        "original_thickness": kept["version"]["metrics"]["bbox"][2],
    }
    checks = (
        published["id"] in seen,
        source.get("model_id") == original["model_id"] and source.get("author") == "alice",
        edit["status"] == "done" and forked["version"]["metrics"]["bbox"][2] == 8,
        kept["versions"] == 1 and kept["version"]["metrics"]["bbox"][2] == 5,
    )
    return evidence("WP-10", m, *checks, note="API half; the web Community tab is not built")


def mock_fea(params: dict[str, float], force_n: float) -> float:
    # root bending stress of a cantilever under a tip load: sigma = M c / I = 6 F L / (w t^2)
    return 6 * force_n * params["length"] / (params["width"] * params["thickness"] ** 2)


def cd_3(rig: Rig) -> Evidence:
    result = fixture("fea_result.json")
    [over] = result["results"]
    allowable = over["allowable_mpa"]
    with serve(rig, rig.llm) as api:
        job = build(api, api.project(), fixture("cantilever.json"))
        before = {p["name"]: p["value"] for p in api.version(job["model_id"])["params"]}
        force = over["max_stress_mpa"] * before["width"] * before["thickness"] ** 2 / (6 * before["length"])
        proposals = api.ok("POST", f"/models/{job['model_id']}/simulation", json=result)
        thicker = next((s for s in proposals if s["change"].get("thickness", 0) > before["thickness"]), None)
        after = before
        if thicker:
            api.wait(api.ok("POST", f"/models/{job['model_id']}/suggestions/{thicker['id']}/accept")["id"])
            after = {p["name"]: p["value"] for p in api.version(job["model_id"])["params"]}
    aluminium = material("Aluminum 6061")
    assert aluminium is not None
    m: Measured = {
        "allowable_mpa": allowable,
        "safety_factor": round(aluminium.yield_mpa / allowable, 3),
        "ratio_before": round(over["max_stress_mpa"] / allowable, 3),
        "load_n": round(force, 2),
        "proposal": json.dumps(thicker["change"]) if thicker else json.dumps([s["change"] for s in proposals]),
        "thickness_after": after["thickness"],
        "stress_after_mpa": round(mock_fea(after, force), 2),
    }
    checks = (abs(over["max_stress_mpa"] / allowable - 1.4) < 1e-9, thicker is not None, mock_fea(after, force) < allowable)
    return evidence("CD-3", m, *checks, note="mock FEA: sigma = 6 F L / (w t^2) at mount_face, F fixed from the fixture result")


def cd_7(rig: Rig) -> Evidence:
    steel = fixture("plate.json")
    steel["parts"][0]["material"] = "steel"
    with serve(rig, Seeded([])) as api:
        project = api.project()
        plate = api.ok("GET", f"/models/{build(api, project, steel)['model_id']}/sensitivities")
        tab = api.ok("GET", f"/models/{build(api, project, fixture('cantilever.json'))['model_id']}/sensitivities")
    d = {p["name"]: p["d"] for p in plate["params"]}
    t = {p["name"]: p["d"] for p in tab["params"]}
    holes = 4 * math.pi * 3.3**2
    expected = {
        "plate dV/dthickness": (d["thickness"]["volume"], 120 * 80 - holes),
        "plate dm/dthickness": (d["thickness"]["mass_g"], (120 * 80 - holes) * 7.85 / 1000),
        "plate dV/dlength": (d["length"]["volume"], 80 * 5),
        "plate dV/dhole_d": (d["hole_d"]["volume"], -4 * math.pi * 6.6 / 2 * 5),
        "plate dbbox_x/dlength": (d["length"]["bbox_x"], 1.0),
        "plate dbbox_z/dthickness": (d["thickness"]["bbox_z"], 1.0),
        "tab dm/dthickness": (t["thickness"]["mass_g"], 80 * 30 * 2.70 / 1000),
        "tab dbbox_y/dwidth": (t["width"]["bbox_y"], 1.0),
    }
    errors = {k: abs(got - want) / abs(want) for k, (got, want) in expected.items()}
    m: Measured = {k: round(got, 5) for k, (got, _) in expected.items()}
    m = {**m, "max_rel_error": f"{max(errors.values()):.2e}", "unchanged dbbox_y/dlength": d["length"]["bbox_y"]}
    return evidence(
        "CD-7", m, max(errors.values()) < 1e-3, abs(d["length"]["bbox_y"]) < 1e-9, note="central differences, 1e-3 relative step"
    )


def cx_12(rig: Rig) -> Evidence:
    archive = rig.out / "archive"
    shutil.rmtree(archive, ignore_errors=True)
    files = make_archive(archive, rig.geometry)
    start = time.monotonic()
    with LocalContext(rig.out / "context", HashEmbedder(), describe=rig.geometry.describe) as ctx:
        outcomes = ingest_all(ctx, "archive", archive_files([archive]))
    report = [o.model_dump() for o in outcomes]
    (rig.out / "ingest_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    parsed = [o for o in outcomes if o.status == "parsed"]
    failed = {o.name: o.error for o in outcomes if o.status == "failed"}
    m: Measured = {
        "files": len(outcomes),
        "step": sum(f.suffix == ".step" for f in files),
        "pdf": sum(f.suffix == ".pdf" for f in files),
        "parsed": len(parsed),
        "rate": round(len(parsed) / len(outcomes), 4),
        "facts": sum(o.facts for o in parsed),
        "failed": "; ".join(f"{n}: {e}" for n, e in failed.items())[:300],
        "seconds": round(time.monotonic() - start, 1),
    }
    checks = (len(outcomes) == 70, len(parsed) / len(outcomes) >= 0.95, all(failed.values()), set(failed) == {BROKEN_STEP, BROKEN_PDF})
    return evidence("CX-12", m, *checks, note="one damaged STEP and one damaged PDF on purpose; report in ingest_report.json")


def cx_14(rig: Rig) -> Evidence:
    with serve(rig, Seeded([])) as api:
        job = build(api, api.project(), fixture("plate.json"))
        [found] = api.ok("GET", "/materials", params={"q": "Aluminum 6061"})
        api.wait(api.ok("PUT", f"/models/{job['model_id']}/material", json={"material": "Aluminum 6061"})["id"])
        metrics = api.version(job["model_id"])["metrics"]
        [part] = api.ok("GET", f"/models/{job['model_id']}/components")
    reference = (120 * 80 - 4 * math.pi * 3.3**2) * 5 * 2.70 / 1000
    props = part["properties"] or {}
    m: Measured = {
        "material": part["material"],
        "density_g_cm3": props.get("density_g_cm3"),
        "youngs_modulus_gpa": props.get("youngs_modulus_gpa"),
        "source": found["source"],
        "mass_g": round(metrics["mass_g"], 3),
        "reference_mass_g": round(reference, 3),
        "error_pct": round(abs(metrics["mass_g"] / reference - 1) * 100, 5),
    }
    checks = (props.get("density_g_cm3") == 2.70, props.get("youngs_modulus_gpa") == 68.9, abs(metrics["mass_g"] / reference - 1) <= 0.01)
    return evidence("CX-14", m, *checks, note="reference = analytic plate volume x 2.70 g/cm3 (ASM MA6061T6)")


def ex_5(rig: Rig) -> Evidence:
    design = fixture("plate.json")
    design["parts"][0]["material"] = "Aluminum 6061-T6"
    art = rig.geometry.build(Design.model_validate(design), rig.out / "plate")
    [reread] = rig.geometry.import_step(art.files["step"])
    meta = rig.geometry.step_metadata(art.files["step"])
    [built] = art.parts
    doc = INTEROP_DOC.read_text(encoding="utf-8")
    freecad = next((name for name in FREECAD if shutil.which(name)), None)
    volume_drift = abs(reread.volume - built.volume) / built.volume
    bbox_drift = max(abs(a - b) for a, b in zip(reread.bbox_size, built.bbox_size, strict=True))
    m: Measured = {
        "schema": meta.schema_name,
        "volume_drift": volume_drift,
        "bbox_drift": bbox_drift,
        "solids": reread.solids,
        "valid": reread.valid,
        "material": meta.bodies[0].material,
        "documented": "Export to other CAD systems" in doc,
        "freecad": freecad or "not installed",
    }
    checks = (
        meta.schema_name.startswith("AP242"),
        volume_drift < 1e-6 and bbox_drift < 1e-6,
        reread.solids == 1 and reread.valid and meta.bodies[0].material == "Aluminum 6061-T6",
        "Export to other CAD systems" in doc,
    )
    note = "OCCT round trip only; the FreeCAD half needs FreeCAD installed"
    return evidence("EX-5", m, *checks, freecad is not None, note=note)


ROWS: dict[str, Demo] = {
    "AP-6": ap_6,
    "AP-9": ap_9,
    "DP-19": dp_19,
    "WP-10": wp_10,
    "WP-11": wp_11,
    "WP-12": wp_12,
    "CD-3": cd_3,
    "CD-7": cd_7,
    "CX-12": cx_12,
    "CX-14": cx_14,
    "EX-5": ex_5,
}
