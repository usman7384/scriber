import csv
import json
import math
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from scriber_agent import CheckResult, Grounding, Step, dump_steps, evaluate, generate, overall_size, refine
from scriber_agent.project_context import coverage
from scriber_context import ContextPack, HashEmbedder, LocalContext, derived_from, to_networkx
from scriber_evals.parity import Demo, Evidence, Rig, Value, evidence
from scriber_geometry import Artifact, HoleInfo
from scriber_ir import Design, Process, Rule, RuleSet, design_hash, diff

FIXTURES = Path(__file__).parents[2] / "parity" / "m2"
P = "m2"
SENSOR = "Sensor plate per the project requirements"
MOUNTING = "Mounting plate per the project specification"
KMM = ("kmm_overview.md", "kmm_notes.txt", "kmm_bom.csv")
MILLING: Process = "milling_3axis"
CORNER_PROBE = RuleSet(rules=[Rule(id="corner_probe", kind="min_internal_corner_radius", value=1e6, unit="mm", process=MILLING)])


def context(rig: Rig) -> LocalContext:
    return LocalContext(rig.out / "context", HashEmbedder(), describe=rig.geometry.describe)


def generated(rig: Rig, ctx: LocalContext, request: str, name: str, project: str = P) -> list[Step]:
    grounding = Grounding(pack=ctx.retrieve(project, request), rules=ctx.rules(project))
    out = rig.out / name
    steps = list(generate(request, rig.llm, rig.geometry, out, rig.config.agent.max_repairs, rig.config.agent.seed, grounding))
    _write(out / "steps.json", dump_steps(steps))
    r = steps[-1].result
    if r and r.design:
        ctx.record_generation(project, name, r.design, r.used)
    return steps


def built(steps: list[Step]) -> tuple[Design, Artifact] | None:
    r = steps[-1].result
    return (r.design, r.artifact) if steps[-1].kind == "done" and r and r.design and r.artifact else None


def fixture(name: str) -> Design:
    return Design.model_validate_json((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def holes(art: Artifact, lo: float = 0.0, hi: float = math.inf) -> list[HoleInfo]:
    return [h for p in art.parts for h in p.holes if lo - 1e-6 <= h.diameter <= hi + 1e-6]


def features(g: Any, fact_ids: Sequence[str]) -> list[str]:
    return sorted({n for f in fact_ids if f in g for n in derived_from(g, f) if g.nodes[n]["type"] == "feature"})


def side_walls(stl: Path) -> list[float]:
    mesh = trimesh.load_mesh(stl)
    mid = mesh.bounds.mean(axis=0)
    segments: np.ndarray = trimesh.intersections.mesh_plane(mesh, [0, 0, 1], mid)
    return [*_outer_spans(segments, 0, mid[1]), *_outer_spans(segments, 1, mid[0])]


def _outer_spans(segments: np.ndarray, axis: int, at: float) -> list[float]:
    a, b = segments[:, 0], segments[:, 1]
    other = 1 - axis
    hit = ((a[:, other] - at) * (b[:, other] - at) <= 0) & (np.abs(b[:, other] - a[:, other]) > 1e-12)
    a, b = a[hit], b[hit]
    t = (at - a[:, other]) / (b[:, other] - a[:, other])
    xs = np.unique(np.round(a[:, axis] + t * (b[:, axis] - a[:, axis]), 6))
    return [float(xs[1] - xs[0]), float(xs[-1] - xs[-2])] if len(xs) >= 4 else []


def fmt(values: Sequence[float]) -> str:
    return " x ".join(f"{v:.3f}" for v in values)


def failed(row: str, what: str = "no design was built") -> Evidence:
    return evidence(row, {"built": False}, False, note=what)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def spec_holes() -> list[tuple[float, float]]:
    with (FIXTURES / "holes.csv").open(encoding="utf-8") as f:
        return [(float(r[1]), float(r[2])) for r in list(csv.reader(f))[1:]]


def plate_match(art: Artifact) -> tuple[dict[str, Value], list[bool]]:
    size = overall_size(art)
    x0, y0 = (min(p.bbox_min[i] for p in art.parts) for i in range(2))
    found = holes(art)
    through = [h for h in found if abs(abs(h.axis[2]) - 1) < 1e-6 and abs(h.length - size[2]) <= 0.01]
    errors = [min((math.dist((h.center[0] - x0, h.center[1] - y0), xy) for h in through), default=math.inf) for xy in spec_holes()]
    m: dict[str, Value] = {
        "size": fmt(size),
        "holes": len(found),
        "through_holes": len(through),
        "max_centre_error_mm": round(max(errors), 4),
    }
    checks = [all(abs(a - b) <= 0.1 for a, b in zip(size, (200, 120, 5), strict=True)), len(found) == 10, len(through) == 10]
    return m, [*checks, max(errors) <= 0.05]


def in_2(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        ctx.ingest(P, FIXTURES / "plate_spec.md")
        got = built(generated(rig, ctx, "Plate as given in the uploaded specification", "plate"))
    if got is None:
        return failed("IN-2")
    m, checks = plate_match(got[1])
    return evidence("IN-2", m, *checks)


def in_3(rig: Rig) -> Evidence:
    arts: dict[str, Artifact] = {}
    with context(rig) as ctx:
        for kind in ("csv", "xlsx"):
            ctx.ingest(kind, FIXTURES / f"holes.{kind}")
            got = built(generated(rig, ctx, "Plate 200 x 120 x 5 mm with the holes from the uploaded hole table", kind, project=kind))
            if got is None:
                return failed("IN-3", f"no design was built from holes.{kind}")
            arts[kind] = got[1]
    (m_csv, c_csv), (m_xlsx, c_xlsx) = plate_match(arts["csv"]), plate_match(arts["xlsx"])
    same = _fingerprint(arts["csv"]) == _fingerprint(arts["xlsx"])
    m: dict[str, Value] = {**{f"csv_{k}": v for k, v in m_csv.items()}, **{f"xlsx_{k}": v for k, v in m_xlsx.items()}, "identical": same}
    return evidence("IN-3", m, same, c_csv[3], c_xlsx[3])


def _fingerprint(art: Artifact) -> tuple[object, ...]:
    centres = sorted((round(h.center[0], 6), round(h.center[1], 6), round(h.diameter, 6)) for h in holes(art))
    return tuple(round(s, 6) for s in overall_size(art)), round(sum(p.volume for p in art.parts), 4), tuple(centres)


def in_9(rig: Rig) -> Evidence:
    source = rig.geometry.build(fixture("bracket"), rig.out / "source")
    upload = rig.out / "bracket.step"
    shutil.copyfile(source.files["step"], upload)
    with context(rig) as ctx:
        ctx.ingest(P, upload)
        got = built(generated(rig, ctx, "same bracket, 20 % longer", "longer"))
    if got is None:
        return failed("IN-9")
    before, after = sorted(overall_size(source)), sorted(overall_size(got[1]))
    m: dict[str, Value] = {"source": fmt(before), "output": fmt(after), "length_ratio": round(after[2] / before[2], 4)}
    others = all(abs(a - b) <= 0.05 for a, b in zip(after[:2], before[:2], strict=True))
    return evidence("IN-9", m, abs(after[2] - 1.2 * before[2]) <= 0.1, others)


def requirement_part(rig: Rig, row: str, request: str) -> Evidence:
    with context(rig) as ctx:
        doc = ctx.ingest(P, FIXTURES / "requirements.pdf")
        got = built(generated(rig, ctx, request, "part"))
        facts = {f.name: f.id for f in ctx.facts(P, doc.id)}
        g = to_networkx(ctx.graph(P))
    if got is None:
        return failed(row)
    art = got[1]
    mount, bore = holes(art, 6.4, 6.6), holes(art, 81.8, 82.2)
    traced = {req: features(g, [facts[name]]) for req, name in (("req_1", "req_1_mount"), ("req_2", "req_2_bore"))}
    valid = art.ok and all(p.valid for p in art.parts)
    m: dict[str, Value] = {"m6_clearance_holes": len(mount), "bores": len(bore), "valid": valid}
    m |= {f"{req}_features": ", ".join(fs) for req, fs in traced.items()}
    return evidence(row, m, len(mount) == 4, len(bore) == 1, all(traced.values()), valid)


def in_12(rig: Rig) -> Evidence:
    return requirement_part(rig, "IN-12", SENSOR)


def dp_17(rig: Rig) -> Evidence:
    return requirement_part(rig, "DP-17", "Sensor housing per the project requirements")


def in_13(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        doc = ctx.ingest(P, FIXTURES / "design-rules.md")
        rule = next(r for r in ctx.rules(P).rules if r.id == "min_hole_edge_ratio")
        steps = generated(rig, ctx, "Plate 100 x 60 x 5 mm with four Ø10 holes 8 mm from the edges", "plate")
        g = ctx.graph(P)
    got = built(steps)
    if got is None:
        return failed("IN-13")
    design, art = got
    x0, y0, _ = (min(p.bbox_min[i] for p in art.parts) for i in range(3))
    x1, y1 = x0 + overall_size(art)[0], y0 + overall_size(art)[1]
    tens = holes(art, 9.9, 10.1)
    edge = min((min(h.center[0] - x0, x1 - h.center[0], h.center[1] - y0, y1 - h.center[1]) for h in tens), default=0.0)
    node = next(n.id for n in g.nodes if n.type == "rule" and n.name == rule.id and n.doc_id == doc.id)
    constrains = any(e.src == node and e.dst == f"plate/{p.id}" and e.type == "constrains" for e in g.edges for p in design.parts)
    report = [f"rule {rule.id} ({rule.binding}, {rule.value:g} x D) from {rule.source.ref}: min hole-to-edge {edge:.2f} mm"]
    _write(rig.out / "report.md", "\n".join(report + [f"- {s.kind}: {s.message}" for s in steps]) + "\n")
    r = steps[-1].result
    used = bool(r and rule.id in r.used)
    m: dict[str, Value] = {"holes_d10": len(tens), "min_edge_mm": round(edge, 3), "rule_source": rule.source.ref, "rule_used": used}
    m |= {"rule_constrains_part": constrains, "repairs": r.repairs if r else None}
    from_doc = rule.source.source == "document" and (rule.source.ref or "").startswith(doc.id)
    return evidence("IN-13", m, len(tens) == 4, edge >= 15 - 1e-3, from_doc, used, constrains)


def in_15(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        doc = ctx.ingest(P, FIXTURES / "report.pdf")
        got = built(generated(rig, ctx, "Open-top electronics enclosure 100 x 70 x 40 mm, walls as sized in the report", "enclosure"))
    if got is None:
        return failed("IN-15")
    design, art = got
    walls = side_walls(art.files["stl"])
    cited = [p.name for p in design.params if abs(p.value - 3.2) <= 0.01 and (p.provenance.ref or "").startswith(doc.id)]
    m: dict[str, Value] = {"side_walls": fmt(walls), "params_citing_report": ", ".join(cited)}
    return evidence("IN-15", m, len(walls) == 4, all(abs(w - 3.2) <= 0.01 for w in walls), bool(cited))


def cx_4(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        for name in KMM:
            ctx.ingest(P, FIXTURES / name)
        steps = generated(rig, ctx, "KMM-28 motor mount", "mount")
        edges = {(e.src, e.dst, e.type) for e in ctx.graph(P).edges}
    r = steps[-1].result
    parts = [f"mount/{p.id}" for p in r.design.parts] if r and r.design else []
    related = ("ent:designation:KMM-28", "ent:fastener:M3", "related_to") in edges
    links = {e: any((p, e, "mentions") in edges for p in parts) for e in ("ent:designation:KMM-28", "ent:fastener:M3")}
    m: dict[str, Value] = {"kmm28_related_to_m3": related, "part_mentions_kmm28": links["ent:designation:KMM-28"]}
    m |= {"part_mentions_m3": links["ent:fastener:M3"], "relations": len(edges)}
    return evidence("CX-4", m, related, bool(parts), *links.values())


def cx_7(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        doc = ctx.ingest(P, FIXTURES / "mounting-plate-spec.md")
        steps = generated(rig, ctx, MOUNTING, "plate")
        facts = ctx.facts(P, doc.id)
    r = steps[-1].result
    cov = coverage(facts, r.checks if r else [])
    surfaced = " ".join(s.message for s in steps if s.kind in ("check", "failed"))
    lines = [f"- {f.name} = {f.value} {f.unit} [{f.source.ref}]: {_status(c)}" for f, c in cov]
    _write(rig.out / "verification.md", "\n".join(lines) + "\n")
    failing = [c for _, c in cov if c is not None and not c.passed]
    evaluated = sum(c is not None for _, c in cov)
    m: dict[str, Value] = {
        "constraints": len(cov),
        "evaluated": evaluated,
        "passed": evaluated - len(failing),
        "repairs": r.repairs if r else None,
    }
    return evidence("CX-7", m, len(cov) == 10, evaluated == 10, all(c.requirement.description in surfaced for c in failing))


def _status(c: CheckResult | None) -> str:
    return "not evaluated" if c is None else f"{'pass' if c.passed else 'FAIL'} ({c.actual})"


def cx_8(rig: Rig) -> Evidence:
    request = "small electronics box"
    with context(rig) as ctx:
        ctx.ingest(P, FIXTURES / "Box_Best_Practice.md")
        got = built(generated(rig, ctx, request, "box"))
    if got is None:
        return failed("CX-8")
    walls, m3 = side_walls(got[1].files["stl"]), holes(got[1], 2.25, 4.35)
    m: dict[str, Value] = {"side_walls": fmt(walls), "m3_holes": len(m3), "request_names_conventions": "2.5" in request or "M3" in request}
    note = "bosses counted as holes sized for M3, from tap drill to heat-set insert bore (2.25 to 4.35 mm)"
    return evidence("CX-8", m, len(walls) == 4, all(abs(w - 2.5) <= 0.01 for w in walls), len(m3) == 4, note=note)


def cx_9(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        doc = ctx.ingest(P, FIXTURES / "requirements.pdf")
        facts = ctx.facts(P, doc.id)
    _write(rig.out / "facts.json", json.dumps([f.model_dump(mode="json") for f in facts], indent=2))
    bore = [f for f in facts if f.kind == "tolerance" and f.value == 82.0 and f.unit == "mm" and f.tol == (-0.2, 0.2)]
    mount = [f for f in facts if f.kind == "holes" and f.value == 6.0 and f.unit == "mm" and f.count == 4 and "M6" in f.text]
    sourced = all(f.name and f.source.source == "document" and (f.source.ref or "").startswith(doc.id) for f in facts)
    m: dict[str, Value] = {
        "facts": len(facts),
        "bore": bore[0].name if bore else None,
        "mount": mount[0].name if mount else None,
        "sourced": sourced,
    }
    return evidence("CX-9", m, len(bore) == 1, len(mount) == 1, sourced)


def cx_10(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        ctx.ingest(P, FIXTURES / "requirements.pdf")
        got = built(generated(rig, ctx, SENSOR, "plate"))
    if got is None:
        return failed("CX-10")
    design, art = got
    feats = [f for p in design.parts for f in p.features]
    sources = sorted({f.provenance.source for f in feats})
    saved = art.files["ir"].read_bytes()
    loaded = Design.model_validate_json(saved)
    again = rig.geometry.build(loaded, rig.out / "reloaded")
    identical = loaded == design and again.files["ir"].read_bytes() == saved
    with_intent = sum(bool(f.intent.strip()) for f in feats)
    cited = sum(p.provenance.source == "document" for p in design.params)
    m: dict[str, Value] = {"features": len(feats), "with_intent": with_intent, "feature_sources": ", ".join(sources)}
    m |= {"params_citing_documents": cited, "byte_identical": identical}
    return evidence("CX-10", m, with_intent == len(feats), set(sources) <= {"prompt", "document", "rule", "standard"}, identical)


def cx_11(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        v1 = ctx.ingest(P, FIXTURES / "requirements.pdf")
        generated(rig, ctx, SENSOR, "plate")
        req_3 = [f for f in ctx.facts(P, v1.id) if f.name.startswith("req_3_")]
        derived = features(to_networkx(ctx.graph(P)), [f.id for f in req_3])
        v2 = ctx.ingest(P, FIXTURES / "requirements-v2.pdf")
        changed = ctx.changed(P, v1.id, v2.id)
        stale = ctx.stale(P, changed)
    names = {f.id: f.name for f in req_3}
    m: dict[str, Value] = {
        "req_3_features": ", ".join(derived),
        "changed": ", ".join(names.get(c, c) for c in changed),
        "stale": ", ".join(stale),
    }
    return evidence("CX-11", m, bool(derived), [names.get(c) for c in changed] == ["req_3_plate_size_x"], stale == ["plate"])


def part(sketches: list[dict[str, Any]], features: list[dict[str, Any]]) -> Design:
    return Design.model_validate(
        {"title": "Fixture", "params": [], "parts": [{"id": "p", "name": "P", "sketches": sketches, "features": features}]}
    )


def _extrude(sketch: str, distance: float, **extra: Any) -> dict[str, Any]:
    return {"kind": "extrude", "id": f"body_{sketch}", "name": "Body", "sketch": sketch, "distance": distance, **extra}


def plate(hole_x: float, diameter: float) -> Design:
    at = {"kind": "points", "points": [[hole_x, 0]]}
    hole = {"kind": "hole", "id": "h", "name": "Hole", "plane": {"offset": 5}, "at": at, "diameter": diameter}
    return part([{"id": "s", "entities": [{"kind": "rect", "width": 60, "height": 40}]}], [_extrude("s", 5), hole])


def pocket(corner_radius: float) -> Design:
    cavity = {"kind": "rect", "width": 30, "height": 20, "corner_radius": corner_radius}
    sketches: list[dict[str, Any]] = [
        {"id": "s", "entities": [{"kind": "rect", "width": 60, "height": 40}]},
        {"id": "k", "plane": {"offset": 20}, "entities": [cavity]},
    ]
    return part(sketches, [_extrude("s", 20), {**_extrude("k", -10), "id": "pocket", "mode": "cut"}])


def ledge(underside_from_horizontal: float) -> Design:
    tip = 10 + 20 * math.tan(math.radians(underside_from_horizontal))
    outline = [[0, 0], [20, 0], [20, 10], [40, tip], [40, 35], [0, 35]]
    profile: dict[str, Any] = {"id": "s", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": outline}]}
    return part([profile], [_extrude("s", 10)])


def project_rules(rig: Rig) -> RuleSet:
    with context(rig) as ctx:
        ctx.ingest(P, FIXTURES / "design-rules.md")
        return ctx.rules(P)


def vm_1(rig: Rig) -> Evidence:
    rules = project_rules(rig)
    cases: dict[str, tuple[Design, Process]] = {
        "pocket_sharp": (pocket(0), MILLING),
        "pocket_r4": (pocket(4), MILLING),
        "overhang_70": (ledge(20), "fdm"),
        "overhang_45": (ledge(45), "fdm"),
    }
    errors = {
        name: sorted({f.rule_id for f in rig.geometry.build(d, rig.out / name, rules, process).findings if f.severity == "error"})
        for name, (d, process) in cases.items()
    }
    m: dict[str, Value] = {name: ", ".join(e) or "PASS" for name, e in errors.items()}
    expected = {"pocket_sharp": [f"min_internal_corner_radius@{MILLING}"], "pocket_r4": [], "overhang_70": ["max_overhang_angle@fdm"]}
    return evidence("VM-1", m, errors == {**expected, "overhang_45": []})


def vm_3(rig: Rig) -> Evidence:
    rules = project_rules(rig)
    bindings = {r.id: r.binding for r in rules.rules if r.source.source == "document"}

    def ready(design: Design, name: str) -> tuple[list[str], Artifact | None]:
        def build(d: Design, out: Path) -> Artifact:
            return rig.geometry.build(d, out, rules)

        problems, _, art, _ = evaluate(design.model_dump_json(), Design.model_validate_json, [], build, rig.out / name)
        return problems, art

    soft, soft_art = ready(plate(0, 2), "dynamic_only")
    hard, hard_art = ready(plate(20, 10), "static")
    warnings = [f.rule_id for f in soft_art.findings if f.severity == "warning"] if soft_art else []
    m: dict[str, Value] = {
        **bindings,
        "dynamic_only_problems": len(soft),
        "dynamic_only_warnings": ", ".join(warnings),
        "static_problems": len(hard),
    }
    marked = bindings == {
        "min_hole_edge_ratio": "static",
        f"min_internal_corner_radius@{MILLING}": "static",
        "max_overhang_angle@fdm": "static",
        "min_hole_diameter": "dynamic",
    }
    blocked = bool(hard) and hard_art is not None and not hard_art.ok
    return evidence("VM-3", m, marked, not soft, bool(soft_art and soft_art.ok), warnings == ["min_hole_diameter"], blocked)


def vm_5(rig: Rig) -> Evidence:
    with context(rig) as ctx:
        ctx.ingest("aero", FIXTURES / "strict-edge-rule.md")
        rules = {p: ctx.rules(p) for p in ("aero", "default")}
    near = plate(12, 10)
    found = {
        p: [f for f in rig.geometry.build(near, rig.out / p, r).findings if f.rule_id == "min_hole_edge_ratio"] for p, r in rules.items()
    }
    aero = found["aero"]
    m: dict[str, Value] = {"aero_flags": len(aero), "default_flags": len(found["default"])}
    m |= {"aero_measured_mm": aero[0].measured if aero else None, "aero_required_mm": aero[0].required if aero else None}
    return evidence("VM-5", m, len(aero) == 1, abs((aero[0].measured or 0) - 18) <= 1e-3 if aero else False, not found["default"])


def reshaped(rig: Rig, before: Design, instruction: str) -> tuple[dict[str, Value], list[bool]]:
    rules = project_rules(rig)
    pack = ContextPack(query=instruction, chunks=[], facts=[], rules=[], similar_parts=[], conventions=[])
    grounding = Grounding(pack=pack, rules=rules, process=MILLING)
    agent = rig.config.agent
    steps = list(refine(before, instruction, rig.llm, rig.geometry, rig.out / "refine", agent.max_repairs, agent.seed, grounding))
    _write(rig.out / "refine" / "steps.json", dump_steps(steps))
    r = steps[-1].result
    if not (r and r.design and r.artifact):
        return {"built": False}, [False]
    after = r.design
    first = rig.geometry.build(before, rig.out / "before", rules, MILLING)
    recheck = rig.geometry.build(after, rig.out / "recheck", rules, MILLING)
    radii = [f.measured for f in rig.geometry.build(after, rig.out / "probe", CORNER_PROBE, MILLING).findings if f.measured is not None]
    change = diff(before, after)
    _write(rig.out / "diff.json", change.model_dump_json(indent=2))
    same_size = all(abs(a - b) <= 0.05 for a, b in zip(overall_size(first), overall_size(recheck), strict=True))
    m: dict[str, Value] = {"milling_before": first.ok, "milling_after": recheck.ok, "corner_radii": fmt(sorted(radii))}
    m |= {
        "diff_features": ", ".join(change.features_added + change.features_changed),
        "diff_params": len(change.params),
        "same_size": same_size,
    }
    return m, [not first.ok, recheck.ok, len(radii) >= 4, min(radii, default=0) >= 3 - 1e-3, not change.empty, same_size]


def vm_2(rig: Rig) -> Evidence:
    m, checks = reshaped(rig, pocket(0), "Make this part manufacturable by 3-axis milling")
    return evidence("VM-2", m, *checks)


def cd_5(rig: Rig) -> Evidence:
    before = fixture("bracket-fdm")
    fdm = rig.geometry.build(before, rig.out / "fdm", project_rules(rig), "fdm").ok
    m, checks = reshaped(rig, before, "Switch the manufacturing method from FDM to 3-axis milling")
    lines = [f"{k}: {v}" for k, v in m.items()]
    _write(rig.out / "diff.md", "# FDM -> 3-axis milling\n\n" + "\n".join(f"- {line}" for line in lines) + "\n")
    return evidence("CD-5", {"fdm_passes": fdm, **m}, fdm, *checks)


def cd_8(rig: Rig) -> Evidence:
    design = fixture("bracket")
    art = rig.geometry.build(design, rig.out / "export")
    imported = Design.model_validate_json(art.files["ir"].read_text(encoding="utf-8"))
    rebuilt = rig.geometry.build(imported, rig.out / "reimport")
    from_step = rig.geometry.import_step(art.files["step"])
    intents = [(f.id, f.intent, f.provenance) for p in design.parts for f in p.features]
    kept = [(f.id, f.intent, f.provenance) for p in imported.parts for f in p.features]
    drift = abs(sum(p.volume for p in from_step) - sum(p.volume for p in rebuilt.parts))
    same = design_hash(imported) == design_hash(design)
    m: dict[str, Value] = {
        "params_kept": imported.params == design.params,
        "intents_kept": kept == intents,
        "same_hash": same,
        "volume_drift": drift,
    }
    return evidence("CD-8", m, imported.params == design.params, kept == intents, same, drift <= 1e-6)


COVERAGE_CASES = (
    ("mounting-plate", "mounting-plate-spec.md", MOUNTING),
    ("sensor-plate", "requirements.pdf", SENSOR),
    ("lid", "lid-spec.md", "Lid per the project specification"),
)


def vm_7(rig: Rig) -> Evidence:
    gaps: dict[str, list[str]] = {}
    m: dict[str, Value] = {}
    with context(rig) as ctx:
        for case, doc_name, request in COVERAGE_CASES:
            doc = ctx.ingest(case, FIXTURES / doc_name)
            r = generated(rig, ctx, request, case, project=case)[-1].result
            cov = coverage(ctx.facts(case, doc.id), r.checks if r else [])
            gaps[case] = [f.name for f, c in cov if c is None]
            m[case] = f"{len(cov) - len(gaps[case])}/{len(cov)} evaluated" + (
                f", unevaluated: {', '.join(gaps[case])}" if gaps[case] else ""
            )
    m["gate"] = "fail" if any(gaps.values()) else "pass"
    _write(rig.out / "coverage.md", "\n".join(f"- {k}: {v}" for k, v in m.items()) + "\n")
    note = "lid-spec.md plants a wall thickness no check covers; the gate must fail on it"
    return evidence("VM-7", m, gaps["lid"] == ["wall_thickness"], m["gate"] == "fail", note=note)


ROWS: dict[str, Demo] = {
    "IN-2": in_2,
    "IN-3": in_3,
    "IN-9": in_9,
    "IN-12": in_12,
    "IN-13": in_13,
    "IN-15": in_15,
    "CX-4": cx_4,
    "CX-7": cx_7,
    "CX-8": cx_8,
    "CX-9": cx_9,
    "CX-10": cx_10,
    "CX-11": cx_11,
    "VM-1": vm_1,
    "VM-2": vm_2,
    "VM-3": vm_3,
    "VM-5": vm_5,
    "VM-7": vm_7,
    "CD-5": cd_5,
    "CD-8": cd_8,
    "DP-17": dp_17,
}
