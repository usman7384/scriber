import io
import itertools
import json
import math
import statistics
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import trimesh
from PIL import Image

from scriber_evals.parity import Demo, Evidence, Measured, Rig, evidence
from scriber_evals.parity_api import NO_REQS, Api, Gate, Seeded, log_lines, serve
from scriber_evals.parity_m1 import VALIDATOR, _gltf_json
from scriber_ir import Design, design_hash
from scriber_ir.model import Path as SketchPath
from scriber_ir.model import Point, Polygon

FIXTURES = Path(__file__).parents[2] / "parity" / "m3"
PLATE_PROMPT = "Base plate 120 x 80 x 5 mm with four 6.6 mm bolt holes"
BRACKET_PROMPT = "Design a metal bracket with angled support and screw holes"
SIMPLE_PROMPTS = (
    "Rectangular plate 100 x 60 x 5 mm",
    "Washer 20 mm outside diameter, 10 mm inside diameter, 2 mm thick",
    "Cube 30 mm with a 10 mm through hole",
    "Spacer tube 12 mm outside diameter, 8 mm inside diameter, 25 mm long",
    "Square plate 80 x 80 x 4 mm with four 5 mm holes on a 60 mm square",
    "Round disc 70 mm diameter, 6 mm thick",
    "Block 60 x 40 x 20 mm",
    "Flat bar 200 x 25 x 6 mm with two 8 mm holes 150 mm apart",
    "Cylinder 40 mm diameter, 60 mm tall",
    "Mounting plate 120 x 80 x 6 mm with four M6 clearance holes",
)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def seed(api: Api, project: str, prompt: str = PLATE_PROMPT) -> str:
    job = api.generate(project, prompt)
    if job["status"] != "done":
        raise RuntimeError(f"the seeded design did not build: {job['error']}")
    model_id: str = job["model_id"]
    return model_id


def seeded(rig: Rig | None = None, *names: str) -> Seeded:
    answers = [a for n in names or ("base_plate.json",) for a in (NO_REQS, fixture(n))]
    return Seeded(answers, rig.llm if rig else None)


def patch(api: Api, model_id: str, values: dict[str, float]) -> dict[str, Any]:
    return api.wait(api.ok("PATCH", f"/models/{model_id}/params", json={"values": values})["id"])


def hole_xs(api: Api, model_id: str, number: int) -> list[float]:
    parts = api.result(model_id, number)["artifact"]["parts"]
    return sorted({round(h["center"][0], 4) for p in parts for h in p["holes"]})


def until(condition: Callable[[], bool], timeout: float = 600) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError("condition not met")
        time.sleep(0.05)


def png_size(api: Api, url: str) -> tuple[int, int]:
    with Image.open(io.BytesIO(api.call("GET", url).content)) as image:
        return image.size


def in_17(rig: Rig) -> Evidence:
    with serve(rig, seeded(rig), vision=rig.vision) as api:
        model_id = api.wait(api.ok("POST", "/api/v1/generate", json={"prompt": PLATE_PROMPT})["job_id"])["model_id"]
        photo = api.upload("default", "photo.png", (FIXTURES / "sketch.png").read_bytes())
        body = {"model_id": model_id, "prompt": "Make it match the photo: 150 x 90 mm", "attachments": [photo["id"]]}
        response = api.call("POST", "/api/v1/modify", json=body)
        job = api.wait(response.json()["job_id"])
        version = api.version(model_id, job["version"]) if job["version"] else {"attachments": [], "inputs": []}
    roles = {i["id"]: i["role"] for i in version["inputs"] if i["kind"] == "file"}
    m: Measured = {"status_code": response.status_code, "job": job["status"], "photo_role": roles.get(photo["id"])}
    m = {**m, "attachments": ", ".join(version["attachments"]), "photo_id": photo["id"]}
    note = "the image goes to the model with the change request; what the model makes of it is the live run's"
    return evidence(
        "IN-17", m, response.status_code == 202, photo["id"] in version["attachments"], roles.get(photo["id"]) == "used", note=note
    )


def edit_latency(rig: Rig, row: str, spacings: tuple[float, ...]) -> Evidence:
    llm = seeded()
    with serve(rig, llm) as api:
        model_id = seed(api, api.project())
        calls = llm.calls
        label = {p["name"]: p["label"] for p in api.version(model_id, 1)["params"]}["base_bolt_spacing_x"]
        rebuild, wall = [], []
        for spacing in spacings:
            start = time.monotonic()
            job = patch(api, model_id, {"base_bolt_spacing_x": spacing})
            wall.append((time.monotonic() - start) * 1000)
            rebuild.append(job["steps"][-1]["elapsed_ms"])
        xs = hole_xs(api, model_id, len(spacings) + 1)
    p50 = statistics.median(rebuild)
    m: Measured = {"label": label, "spacing": round(xs[1] - xs[0], 4), "llm_calls": llm.calls - calls, "edits": len(spacings)}
    m = {**m, "rebuild_p50_ms": p50, "rebuild_max_ms": max(rebuild), "job_wall_p50_ms": round(statistics.median(wall))}
    checks = (abs(xs[1] - xs[0] - spacings[-1]) <= 0.01, llm.calls == calls, p50 < 1000, label == "Base Bolt Spacing X")
    return evidence(row, m, *checks, note="rebuild = kernel build and export; job wall adds thumbnail, shape descriptor and graph record")


def pr_2(rig: Rig) -> Evidence:
    return edit_latency(rig, "PR-2", (86, 87, 88, 89, 90))


def pf_4(rig: Rig) -> Evidence:
    return edit_latency(rig, "PF-4", (86, 87, 88, 89, 90, 91, 92, 93, 94, 90))


def pr_9(rig: Rig) -> Evidence:
    with serve(rig, seeded()) as api:
        model_id = seed(api, api.project())
        for width in (90, 100, 110):
            patch(api, model_id, {"width": width})
        history = api.ok("GET", f"/models/{model_id}/versions")
        sizes = [png_size(api, v["thumbnail_url"]) if v["thumbnail_url"] else None for v in history]
        restored = api.ok("POST", f"/models/{model_id}/versions/1/restore")
    with_prompt = sum(bool(v["prompt"]) for v in history)
    m: Measured = {
        "versions": len(history),
        "with_prompt": with_prompt,
        "png_256": sizes.count((256, 256)),
        "restored_as": restored["number"],
    }
    same = restored["params"] == history[0]["params"]
    return evidence("PR-9", {**m, "params_equal_v1": same}, len(history) == 4, with_prompt == 4, sizes.count((256, 256)) == 4, same)


def ex_6(rig: Rig) -> Evidence:
    with serve(rig, seeded(), auth="tokens") as api:
        auth = {"X-API-Token": api.ok("POST", "/tokens", json={"name": "owner"})["token"]}
        api.client.headers.update(auth)
        model_id = seed(api, api.project())
        share = api.ok("POST", "/shares", json={"model_id": model_id})
        api.client.headers.pop("X-API-Token")
        viewed = api.call("GET", share["url"])
        glb = api.call("GET", f"{share['url']}/files/glb").content
        write = api.call("PATCH", f"/models/{model_id}/params", json={"values": {"width": 90}}).status_code
        revoked = api.call("DELETE", f"/shares/{share['id']}", headers=auth).status_code
        after = api.call("GET", share["url"]).status_code
    m: Measured = {"view": viewed.status_code, "glb_magic": glb[:4].decode(errors="replace"), "write": write, "revoke": revoked}
    m = {**m, "after_revoke": after}
    note = "API half; the read-only viewer page is the web suite's"
    return evidence("EX-6", m, viewed.status_code == 200, glb[:4] == b"glTF", write == 401, revoked == 204, after == 404, note=note)


def ex_7(rig: Rig) -> Evidence:
    received: list[dict[str, Any]] = []

    def plm(request: httpx.Request) -> httpx.Response:
        received.append({"url": str(request.url), "body": json.loads(request.content)})
        return httpx.Response(503 if len(received) <= 2 else 200)

    with serve(rig, seeded(), transport=httpx.MockTransport(plm)) as api:
        api.ok("POST", "/hooks", json={"url": "http://plm.test/hook", "events": ["version.created"]})
        model_id = seed(api, api.project())
        until(lambda: len(received) >= 3, 60)
        payload = received[-1]["body"]
        step = api.call("GET", payload["files"]["step"].removeprefix("http://127.0.0.1:8000")).content
    (rig.out / "plm.jsonl").write_text("".join(json.dumps(r) + "\n" for r in received), encoding="utf-8")
    keys = sorted(k for k in payload if k != "event")
    m: Measured = {"deliveries": len(received), "keys": ", ".join(keys), "version": payload["version"], "step_bytes": len(step)}
    ok = keys == ["files", "model_id", "version"] and payload["model_id"] == model_id
    return evidence("EX-7", m, ok, len(received) == 3, received[0]["body"] == payload, step.startswith(b"ISO-10303-21"))


def ap_1(rig: Rig) -> Evidence:
    with serve(rig, Seeded([]), auth="tokens") as api:
        anonymous = api.call("GET", "/projects").status_code
        first = api.ok("POST", "/tokens", json={"name": "ci"})["token"]
        bearer = api.call("GET", "/projects", headers={"Authorization": f"Bearer {first}"}).status_code
        header = api.call("GET", "/projects", headers={"X-API-Token": first}).status_code
        second = api.ok("POST", "/tokens", json={"name": "temp"}, headers={"X-API-Token": first})
        before = api.call("GET", "/projects", headers={"X-API-Token": second["token"]}).status_code
        deleted = api.call("DELETE", f"/tokens/{second['id']}", headers={"X-API-Token": first}).status_code
        after = api.call("GET", "/projects", headers={"Authorization": f"Bearer {second['token']}"}).status_code
    m: Measured = {"anonymous": anonymous, "bearer": bearer, "x_api_token": header, "before_revoke": before, "revoke": deleted}
    m = {**m, "after_revoke": after}
    return evidence("AP-1", m, anonymous == 401, bearer == 200, header == 200, before == 200, deleted == 204, after == 401)


def angled_facet_mm2(stl: bytes) -> float:
    mesh = trimesh.load_mesh(io.BytesIO(stl), file_type="stl")
    normals = np.abs(mesh.facets_normal) if len(mesh.facets) else np.zeros((0, 3))
    angled = normals.max(axis=1) < math.cos(math.radians(1)) if len(normals) else np.zeros(0, dtype=bool)
    return float(mesh.facets_area[angled].max()) if angled.any() else 0.0


def angled_features(design: Design) -> list[str]:
    found = []
    for part in design.parts:
        for sketch in part.sketches:
            outlines = [e.points for e in sketch.entities if isinstance(e, Polygon)]
            outlines += [[e.start, *(s.to for s in e.segments)] for e in sketch.entities if isinstance(e, SketchPath)]
            found += [f"{part.id}.{sketch.id}" for points in outlines if _sloped(points)]
        found += [f"{part.id}.{d.id}" for d in part.datums if d.rotate_about != "none" and d.angle != 0]
        found += [f"{part.id}.{f.id}" for f in part.features if getattr(f, "taper", 0) != 0]
    return found


def _sloped(points: list[Point]) -> bool:
    numeric = [(x, y) for x, y in points if isinstance(x, float | int) and isinstance(y, float | int)]
    if len(numeric) < len(points):
        return True
    ring = [*numeric, numeric[0]]
    return any(abs(b[0] - a[0]) > 1e-6 and abs(b[1] - a[1]) > 1e-6 for a, b in itertools.pairwise(ring))


def ap_2(rig: Rig) -> Evidence:
    with serve(rig, rig.llm) as api:
        response = api.ok("POST", "/api/v1/generate", json={"prompt": BRACKET_PROMPT})
        job = api.wait(response["job_id"])
        if job["status"] != "done":
            return evidence("AP-2", {"job_id": response["job_id"], "job": job["status"], "error": job["error"]}, False)
        version = api.version(job["model_id"])
        stl = api.call("POST", "/api/v1/download", json={"model_id": job["model_id"], "format": "stl"}).content
        design = Design.model_validate_json(api.call("GET", f"/models/{job['model_id']}/export", params={"fmt": "ir"}).content)
    facet, features = angled_facet_mm2(stl), angled_features(design)
    m: Measured = {"job_id": response["job_id"], "holes": version["metrics"]["holes"], "angled_facet_mm2": round(facet, 1)}
    m = {**m, "angled_features": ", ".join(features), "title": design.title}
    return evidence("AP-2", m, version["metrics"]["holes"] >= 1, bool(features), facet >= 50)


def ap_3(rig: Rig) -> Evidence:
    with serve(rig, seeded(rig)) as api:
        model_id = api.wait(api.ok("POST", "/api/v1/generate", json={"prompt": PLATE_PROMPT})["job_id"])["model_id"]
        before = api.version(model_id)["metrics"]["bbox"][2]
        job = api.wait(api.ok("POST", "/api/v1/modify", json={"model_id": model_id, "prompt": "make it 10 mm thicker"})["job_id"])
        after = api.version(model_id, job["version"])["metrics"] if job["status"] == "done" else None
    thickness = after["bbox"][2] if after else None
    m: Measured = {"before": before, "after": thickness, "job": job["status"]}
    return evidence(
        "AP-3", m, thickness is not None and abs(thickness - before - 10) <= 0.01, note="seeded 5 mm plate; the change is the model's"
    )


def ap_4(rig: Rig) -> Evidence:
    with serve(rig, seeded(None, "base_and_boss.json")) as api:
        model_id = api.wait(api.ok("POST", "/api/v1/generate", json={"prompt": "Base plate with a boss"})["job_id"])["model_id"]
        body = {"model_id": model_id, "component_id": "boss", "params": {"boss_d": 30}}
        job = api.wait(api.ok("POST", "/api/v1/edit", json=body)["job_id"])
        foreign = api.call("POST", "/api/v1/edit", json={**body, "params": {"plate_t": 6}}).status_code
        before, after = (_parts(api, model_id, n) for n in (1, 2))
        irs = [_ir_parts(api, model_id, n) for n in (1, 2)]
        changed = [p["name"] for p in api.version(model_id, 2)["changes"]["params"]]
    boss = round(after["boss"]["bbox_size"][0], 4)
    m: Measured = {"job": job["status"], "boss_x": boss, "foreign_param": foreign, "params_changed": ", ".join(changed)}
    m = {**m, "base_metrics_same": before["base"] == after["base"], "base_ir_same": irs[0]["base"] == irs[1]["base"]}
    same = before["base"] == after["base"] and irs[0]["base"] == irs[1]["base"]
    return evidence("AP-4", m, job["status"] == "done", same, boss == 30, changed == ["boss_d"], foreign == 400)


def _parts(api: Api, model_id: str, number: int) -> dict[str, dict[str, Any]]:
    return {p["id"]: p for p in api.result(model_id, number)["artifact"]["parts"]}


def _ir_parts(api: Api, model_id: str, number: int) -> dict[str, str]:
    design = Design.model_validate_json(api.call("GET", f"/models/{model_id}/export", params={"fmt": "ir", "version": number}).content)
    return {p.id: p.model_dump_json() for p in design.parts}


def hole_chord_error(mesh: trimesh.Trimesh, holes: list[dict[str, Any]]) -> float:
    worst = 0.0
    for h in holes:
        cx, cy, r = h["center"][0], h["center"][1], h["diameter"] / 2
        corners = mesh.vertices[mesh.faces]
        radial = np.hypot(corners[..., 0] - cx, corners[..., 1] - cy)
        wall = np.all(np.abs(radial - r) < 1e-3, axis=1)
        mids = (corners[wall] + corners[wall][:, [1, 2, 0]]) / 2
        worst = max(worst, float(np.max(np.abs(np.hypot(mids[..., 0] - cx, mids[..., 1] - cy) - r))))
    return worst


def ap_5(rig: Rig) -> Evidence:
    with serve(rig, seeded()) as api:
        model_id = seed(api, api.project())
        files = {f: api.call("POST", "/api/v1/download", json={"model_id": model_id, "format": f}).content for f in ("glb", "step", "stl")}
        version, holes = api.version(model_id, 1), api.result(model_id, 1)["artifact"]["parts"][0]["holes"]
    for fmt, content in files.items():
        (rig.out / f"model.{fmt}").write_bytes(content)
    reloaded = rig.geometry.import_step(rig.out / "model.step")
    drift = abs(sum(p.volume for p in reloaded) - version["metrics"]["volume"])
    mesh = trimesh.load_mesh(rig.out / "model.stl")
    chord = hole_chord_error(mesh, holes)
    report = json.loads(
        subprocess.run(["node", str(VALIDATOR), str(rig.out / "model.glb")], capture_output=True, text=True, check=True).stdout
    )
    (rig.out / "validator.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    nodes = sorted(str(n.get("name", "")) for n in _gltf_json(rig.out / "model.glb")["nodes"] if "mesh" in n)
    schema = "AP214" if b"AUTOMOTIVE_DESIGN" in files["step"] else "other"
    solids, errors = sum(p.solids for p in reloaded), int(report["issues"]["numErrors"])
    m: Measured = {"step_schema": schema, "step_solids": solids, "volume_drift": drift, "stl_watertight": bool(mesh.is_watertight)}
    m = {**m, "chordal_deviation_mm": round(chord, 5), "gltf_errors": errors, "mesh_nodes": ", ".join(nodes)}
    checks = (schema == "AP214", solids == 1, drift <= 1e-6, bool(mesh.is_watertight), chord <= 0.05, errors == 0, nodes == ["Plate"])
    return evidence("AP-5", m, *checks)


def ap_7(rig: Rig) -> Evidence:
    with serve(rig, rig.llm) as api:
        project = api.project()
        batch = api.ok("POST", "/batch", json={"project_id": project, "prompts": list(SIMPLE_PROMPTS)})
        jobs = [api.wait(j["id"]) for j in batch["jobs"]]
        models = api.ok("GET", f"/projects/{project}/models")
    done = sum(j["status"] == "done" for j in jobs)
    listed = sum(m["latest_version"] is not None for m in models)
    m: Measured = {
        "jobs": len(jobs),
        "done": done,
        "listed": listed,
        "failed": ", ".join(j["error"] or "" for j in jobs if j["status"] != "done"),
    }
    return evidence("AP-7", m, len(jobs) == 10, done == 10, listed == 10)


def cd_1(rig: Rig) -> Evidence:
    spec = fixture("beam_spec.md")
    with serve(rig, rig.llm) as api:
        project = api.project()
        api.upload(project, "beam_spec.md", spec.encode())
        first = api.generate(project, "Rectangular support beam to the project spec, span along X")
        if first["status"] != "done":
            return evidence("CD-1", {"generate": first["status"], "error": first["error"]}, False)
        model_id = first["model_id"]
        api.upload(project, "beam_spec.md", spec.replace("1000 mm", "1100 mm").encode())
        until(lambda: any(j["kind"] in ("params", "refine") for j in api.ok("GET", f"/projects/{project}/jobs")), 60)
        [auto] = [j for j in api.ok("GET", f"/projects/{project}/jobs") if j["kind"] in ("params", "refine")]
        job = api.wait(auto["id"])
        history = api.ok("GET", f"/models/{model_id}/versions")
    v1, latest = history[0], history[-1]
    span = max(latest["metrics"]["bbox"]) if latest["metrics"] else None
    m: Measured = {"auto_job": auto["kind"], "job": job["status"], "v1_span": max(v1["metrics"]["bbox"]), "new_span": span}
    m = {**m, "versions": len(history), "origin": latest["origin"], "trigger": latest["prompt"]}
    checks = (
        latest["origin"] == "context",
        span is not None and abs(span - 1100) <= 1,
        v1["status"] == "ok",
        abs(max(v1["metrics"]["bbox"]) - 1000) <= 1,
    )
    return evidence("CD-1", m, *checks, note="params job = cited parameter rebuilt without the model; refine job = the model was asked")


def cd_2(rig: Rig) -> Evidence:
    filleted = json.loads(fixture("base_plate.json"))
    filleted["params"].append({"name": "edge_r", "value": 1, "unit": "mm"})
    filleted["parts"][0]["features"].append(
        {"kind": "fillet", "id": "fillet", "name": "Edge fillet", "edges": {"of": "body", "parallel": "z"}, "radius": "edge_r"}
    )
    llm = Seeded([NO_REQS, fixture("base_plate.json"), NO_REQS, json.dumps({"updates": [], "design": filleted})])
    with serve(rig, llm) as api:
        model_id = seed(api, api.project())
        patch(api, model_id, {"base_bolt_spacing_x": 90})
        api.wait(api.ok("POST", f"/models/{model_id}/refine", json={"instruction": "round the vertical edges with 1 mm fillets"})["id"])
        api.ok("POST", f"/models/{model_id}/versions/1/restore")
        history = api.ok("GET", f"/models/{model_id}/versions")
    report = change_report(history)
    (rig.out / "change_report.md").write_text(report, encoding="utf-8")
    edits = history[1:]
    params = edits[0]["changes"]["params"]
    added = edits[1]["changes"]["features_added"] if edits[1]["changes"] else []
    sourced = all(v["origin"] and v["prompt"] for v in edits)
    m: Measured = {"versions": len(history), "param_change": json.dumps(params), "features_added": ", ".join(added)}
    m = {**m, "sources": ", ".join(f"{v['origin']}: {v['prompt']}" for v in edits)}
    ok_params = params == [{"name": "base_bolt_spacing_x", "old": 85.0, "new": 90.0}]
    return evidence("CD-2", m, ok_params, added == ["plate.fillet"], sourced, edits[2]["changes"] is not None, note="seeded designs")


def change_report(history: list[dict[str, Any]]) -> str:
    lines = ["# Change report", ""]
    for v in history[1:]:
        lines += [f"## v{v['number']} ({v['origin']}): {v['prompt']}"]
        changes = v["changes"] or {}
        lines += [f"- {p['name']}: {p['old']} -> {p['new']}" for p in changes.get("params", [])]
        for key in ("features_added", "features_removed", "features_changed"):
            lines += [f"- {key.removeprefix('features_')} feature {f}" for f in changes.get(key, [])]
        lines.append("")
    return "\n".join(lines)


def sse(lines: list[str]) -> list[tuple[str, dict[str, Any]]]:
    events, current = [], dict[str, str]()
    for line in [*lines, ""]:
        if not line:
            if "event" in current:
                events.append((current["event"], json.loads(current["data"])))
            current = {}
        elif not line.startswith(":"):
            key, _, value = line.partition(": ")
            current[key] = value
    return events


def stream(api: Api, job_id: str) -> list[tuple[str, dict[str, Any]]]:
    with api.client.stream("GET", f"/jobs/{job_id}/events") as response:
        return sse(list(response.iter_lines()))


def wp_6(rig: Rig) -> Evidence:
    with serve(rig, rig.llm) as api:
        project = api.project()
        job = api.ok("POST", f"/projects/{project}/generate", json={"prompt": PLATE_PROMPT})
        events = stream(api, job["id"])
    (rig.out / "sse.jsonl").write_text("".join(json.dumps({"event": e, "data": d}) + "\n" for e, d in events), encoding="utf-8")
    progress = [d["progress"] for e, d in events if e == "step"]
    rising = all(a <= b for a, b in itertools.pairwise(progress))
    m: Measured = {"step_events": len(progress), "progress": ", ".join(map(str, progress)), "final": events[-1][0] if events else None}
    return evidence(
        "WP-6", m, len(progress) >= 3, rising, progress[-1:] == [100], m["final"] == "done", note="API half; the bar is the web suite's"
    )


def wp_7(rig: Rig) -> Evidence:
    garbage = [f"not json {i}" for i in range(rig.config.agent.max_repairs + 1)]
    gate = Gate(Seeded([NO_REQS, fixture("base_plate.json"), NO_REQS, *garbage]))
    with serve(rig, gate) as api:
        project = api.project()
        queued = api.ok("POST", f"/projects/{project}/generate", json={"prompt": PLATE_PROMPT})
        until(lambda: api.ok("GET", f"/jobs/{queued['id']}")["status"] == "running", 60)
        gate.open.set()
        done = api.wait(queued["id"])
        failed = api.generate(project, PLATE_PROMPT)
    finished = [line for line in log_lines(rig) if line.get("event") == "job_finished" and line.get("job_id") == failed["id"]]
    traced = bool(finished) and bool(finished[0].get("request_id")) and finished[0].get("status") == "failed"
    m: Measured = {"submitted": queued["status"], "observed_running": True, "done": done["status"], "failed": failed["status"]}
    m = {**m, "error": failed["error"], "log_job_id": finished[0]["job_id"] if finished else None}
    m = {**m, "log_request_id": finished[0].get("request_id") if finished else None}
    return evidence("WP-7", m, queued["status"] == "queued", done["status"] == "done", failed["status"] == "failed", traced)


def in_16(rig: Rig) -> Evidence:
    prompt = "Mounting plate like the attached sketch, built to the attached spec"
    with serve(rig, rig.llm, vision=rig.vision) as api:
        project = api.project()
        sketch = api.upload(project, "sketch.png", (FIXTURES / "sketch.png").read_bytes())
        spec = api.upload(project, "plate_spec.md", fixture("plate_spec.md").encode())
        facts = {f["value"] for f in api.ok("GET", f"/projects/{project}/context/{spec['id']}/facts") if isinstance(f["value"], float)}
        both = api.generate(project, prompt, attachments=[sketch["id"], spec["id"]])
        alone = api.generate(project, prompt, attachments=[sketch["id"]], context_ids=[])
        if both["version"] is None or alone["version"] is None:
            return evidence("IN-16", {"with_spec": both["status"], "without_spec": alone["status"]}, False)
        with_spec, without = api.version(both["model_id"], 1), api.version(alone["model_id"], 1)
    roles = {(i["kind"], i["name"]): i["role"] for i in with_spec["inputs"]}
    expected = {("prompt", None), ("file", "sketch.png"), ("file", "plate_spec.md")}
    p1, p2 = ({p["name"]: p["value"] for p in v["params"]} for v in (with_spec, without))
    driven = sorted(n for n, v in p1.items() if v in facts)
    changed = [n for n in driven if p2.get(n) != p1[n]]
    m: Measured = {"inputs": ", ".join(f"{k[1] or k[0]}={r}" for k, r in roles.items()), "spec_driven": ", ".join(driven)}
    m = {**m, "changed_without_spec": ", ".join(changed), "with_spec": with_spec["status"], "without_spec": without["status"]}
    all_used = set(roles) == expected and set(roles.values()) == {"used"}
    return evidence("IN-16", m, all_used, bool(changed))


def rib_count(stl: bytes) -> int:
    mesh = trimesh.load_mesh(io.BytesIO(stl), file_type="stl")
    z = mesh.bounds[0][2] + 0.75 * (mesh.bounds[1][2] - mesh.bounds[0][2])
    section = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    return len(section.discrete) if section is not None else 0


def ge_9(rig: Rig) -> Evidence:
    with serve(rig, seeded(rig, "ribbed_jaw.json")) as api:
        base = seed(api, api.project(), "Gripper jaw 100 x 40 x 5 mm with 4 ribs, 2 mm thick and 15 mm tall")
        batch = api.ok("POST", f"/models/{base}/variants", json={"instruction": "Generate 3 versions with 4, 6, 8 ribs"})
        jobs = [api.wait(j["id"]) for j in batch["jobs"]]
        ribs = [rib_count(api.call("GET", f"/models/{j['model_id']}/export", params={"fmt": "stl"}).content) for j in jobs if j["version"]]
        start = time.monotonic()
        sweep = api.ok("POST", f"/models/{base}/variants", json={"param": "length", "values": [100 + i for i in range(100)]})
        swept = [api.wait(j["id"]) for j in sweep["jobs"]]
        seconds = time.monotonic() - start
        solids = [_valid_solid(api, j) for j in swept]
    m: Measured = {"variants": len(jobs), "rib_counts": ", ".join(map(str, ribs)), "sweep": len(swept), "sweep_valid": sum(solids)}
    m = {**m, "sweep_seconds": round(seconds, 1)}
    return evidence("GE-9", m, ribs == [4, 6, 8], len(swept) == 100, sum(solids) == 100, note="seeded base; the model plans the variants")


def _valid_solid(api: Api, job: dict[str, Any]) -> bool:
    if job["status"] != "done":
        return False
    parts = api.result(job["model_id"], job["version"])["artifact"]["parts"]
    return all(p["valid"] and p["solids"] == 1 for p in parts)


def ge_13(rig: Rig) -> Evidence:
    logs: dict[str, set[str]] = {"low": set(), "high": set()}
    valid = {"low": 0, "high": 0}
    with serve(rig, rig.llm) as api:
        project = api.project()
        for prompt in SIMPLE_PROMPTS[:5]:
            for level in ("low", "high"):
                job = api.generate(project, prompt, thinking=level)
                valid[level] += job["status"] == "done"
                logs[level] |= {s["message"].rsplit(", thinking ", 1)[-1] for s in job["steps"] if "reasoning budget" in s["message"]}
    m: Measured = {"low_valid": valid["low"], "high_valid": valid["high"], "low_log": " | ".join(logs["low"])}
    m = {**m, "high_log": " | ".join(logs["high"])}
    return evidence("GE-13", m, valid == {"low": 5, "high": 5}, len(logs["low"]) == len(logs["high"]) == 1, logs["low"] != logs["high"])


def pr_7(rig: Rig) -> Evidence:
    with serve(rig, seeded(rig)) as api:
        model_id = seed(api, api.project())
        made = api.ok("POST", f"/models/{model_id}/suggestions")
        if not made:
            return evidence("PR-7", {"suggestions": 0}, False)
        shaped = all(s["target"] and s["change"] and s["rationale"] for s in made)
        before = _ir_hash(api, model_id)
        api.ok("POST", f"/models/{model_id}/suggestions/{made[-1]['id']}/ignore")
        ignored_same = _ir_hash(api, model_id) == before and api.version(model_id)["number"] == 1
        if len(made) < 2:
            made = api.ok("POST", f"/models/{model_id}/suggestions")
        job = api.wait(api.ok("POST", f"/models/{model_id}/suggestions/{made[0]['id']}/accept")["id"])
        values = {p["name"]: p["value"] for p in api.version(model_id)["params"]}
    applied = job["status"] == "done" and all(abs(values[k] - v) <= 1e-9 for k, v in made[0]["change"].items())
    m: Measured = {"suggestions": len(made), "first": json.dumps(made[0]), "ignore_keeps_ir": ignored_same, "accept_applied": applied}
    return evidence("PR-7", m, shaped, ignored_same, applied, note="API half; showing them in 3D is the web suite's")


def _ir_hash(api: Api, model_id: str) -> str:
    return design_hash(Design.model_validate_json(api.call("GET", f"/models/{model_id}/export", params={"fmt": "ir"}).content))


def cx_1(rig: Rig) -> Evidence:
    step = rig.geometry.build(Design.model_validate_json(fixture("base_plate.json")), rig.out / "step").files["step"]
    names = ["bracket_spec.pdf", "plate_spec.md", "notes.txt", "holes.csv", "sketch.png"]
    files = [(n, (FIXTURES / n).read_bytes()) for n in names] + [("base_plate.step", step.read_bytes())]
    with serve(rig, Seeded([])) as api:
        project = api.project()
        jobs = api.ok("POST", f"/projects/{project}/context", files=[("files", (n, c, "application/octet-stream")) for n, c in files])
        progress = [[d["progress"] for e, d in stream(api, j["id"]) if e == "step"] for j in jobs]
        listed = api.ok("GET", f"/projects/{project}/context")["files"]
    statuses = {f["name"]: f["status"] for f in listed}
    m: Measured = {"uploaded": len(files), "listed": len(listed), "processed": sum(s == "processed" for s in statuses.values())}
    m = {**m, "progress": " ".join("/".join(map(str, p)) for p in progress), "kinds": ", ".join(str(f["kind"]) for f in listed)}
    note = "API half; per-file progress bars are the web suite's"
    return evidence("CX-1", m, len(listed) == 6, m["processed"] == 6, all(p == [0, 100] for p in progress), note=note)


def cx_3(rig: Rig) -> Evidence:
    with serve(rig, rig.llm) as api:
        project = api.project()
        a = api.upload(project, "plate_spec.md", fixture("plate_spec.md").encode())
        b = api.upload(project, "notes.txt", fixture("notes.txt").encode())
        c = api.upload(project, "beam_spec.md", fixture("beam_spec.md").encode())
        job = api.generate(project, "Mounting plate to the selected documents", context_ids=[a["id"], b["id"]])
        version = api.version(job["model_id"], 1) if job["version"] else {"inputs": []}
        used_in = {f["id"]: f["used_in"] for f in api.ok("GET", f"/projects/{project}/context")["files"]}
    recorded = [i["id"] for i in version["inputs"] if i["kind"] == "file" and i["role"] == "used"]
    m: Measured = {"job": job["status"], "recorded": ", ".join(recorded), "selected": f"{a['id']}, {b['id']}"}
    m = {**m, "used_in": json.dumps({k: v for k, v in used_in.items()})}
    shown = used_in[a["id"]] == used_in[b["id"]] == [job["model_id"]] and used_in[c["id"]] == []
    return evidence("CX-3", m, recorded == [a["id"], b["id"]], shown, note="API half; the 'Used in' column is the web suite's")


def cx_6(rig: Rig) -> Evidence:
    llm = seeded(None, "base_plate.json", "base_plate.json")
    with serve(rig, llm) as api:
        project = api.project()
        for name in ("plate_spec.md", "holes.csv", "notes.txt"):
            api.upload(project, name, (FIXTURES / name).read_bytes())
        for _ in range(2):
            seed(api, project)
        listing = api.ok("GET", f"/projects/{project}/context")
    s = listing["stats"]
    used = sum(bool(f["used_in"]) for f in listing["files"])
    score = 10 * s["files"] + 2 * s["facts"] + 5 * s["rules"] + 20 * s["used_in_generation"]
    level = math.isqrt(score // 100)
    m: Measured = {k: s[k] for k in ("files", "facts", "rules", "generations", "used_in_generation", "score", "level", "next_level_score")}
    checks = (s["files"] == 3, s["generations"] == 2, s["used_in_generation"] == used, s["score"] == score, s["level"] == level)
    return evidence(
        "CX-6", m, *checks, s["next_level_score"] == 100 * (level + 1) ** 2, note="formula in docs/agents/context.md; UI half is web's"
    )


def pr_10(rig: Rig) -> Evidence:
    with serve(rig, seeded()) as api:
        model_id = seed(api, api.project())
        bbox = api.version(model_id)["metrics"]["bbox"]
        (rig.out / "model.step").write_bytes(api.call("GET", f"/models/{model_id}/export", params={"fmt": "step"}).content)
    kernel = rig.geometry.describe(rig.out / "model.step").bbox_sorted
    m: Measured = {"L": bbox[0], "W": bbox[1], "H": bbox[2], "step_sorted": ", ".join(f"{v:g}" for v in kernel)}
    exact = all(abs(a - b) <= 0.01 for a, b in zip(bbox, (120, 80, 5), strict=True))
    agrees = all(abs(a - b) <= 0.01 for a, b in zip(sorted(bbox), kernel, strict=True))
    return evidence("PR-10", m, exact, agrees, note="API half (version metrics); the on-model labels are the web suite's")


ROWS: dict[str, Demo] = {
    "IN-16": in_16,
    "IN-17": in_17,
    "GE-9": ge_9,
    "GE-13": ge_13,
    "PR-2": pr_2,
    "PR-7": pr_7,
    "PR-9": pr_9,
    "PR-10": pr_10,
    "EX-6": ex_6,
    "EX-7": ex_7,
    "AP-1": ap_1,
    "AP-2": ap_2,
    "AP-3": ap_3,
    "AP-4": ap_4,
    "AP-5": ap_5,
    "AP-7": ap_7,
    "CD-1": cd_1,
    "CD-2": cd_2,
    "WP-6": wp_6,
    "WP-7": wp_7,
    "CX-1": cx_1,
    "CX-3": cx_3,
    "CX-6": cx_6,
    "PF-4": pf_4,
}
