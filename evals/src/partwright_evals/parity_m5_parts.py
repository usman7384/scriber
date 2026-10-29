import ipaddress
import itertools
import json
import math
import socket
import statistics
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from numpy.typing import NDArray
from ollama import Client
from pydantic import BaseModel
from scipy.spatial import ConvexHull

from partwright_agent import CheckResult, check, dump_steps, generate, plan_variants, refine
from partwright_evals import parity_m4_assembly, parity_m4_vision
from partwright_evals.parity import Demo, Evidence, Measured, Rig, Value, evidence
from partwright_evals.parity_api import serve
from partwright_evals.run import Case, load_cases
from partwright_geometry import Artifact, BuildError, HoleInfo, hausdorff
from partwright_ir import Design, apply_params, evaluate, joint_tree
from partwright_ir.model import Extrude, Pattern, Polygon
from partwright_ir.model import Path as SketchPath

ROOT = Path(__file__).parents[2]
PARTS = ROOT / "cases" / "parts.yaml"
BENCHMARK = ROOT / "cases" / "benchmark.yaml"
FIXTURES = ROOT / "parity" / "m5"
DRAWING = "Model the part in the attached dimensioned drawing as one solid, with a named parameter for every dimension shown."
LONGER = "increase length to 450 mm"
RIBS = "Generate 3 versions with 4, 6, 8 ribs"
SERVO_TAB_SPACING = 27.8  # evals/parity/m4/vision/servo_datasheet.md
GUSSETS = {"dp14-single-gusset": 1, "dp14-double-gusset": 2, "dp14-shelf-bracket": 1}
SECONDS_CLAIM = 60.0
# benchmark specs that also meet the API's default DFM rules, so a job can finish without fighting the project rules
OFFLINE = (
    "b02-round-spacer",
    "b03-square-tube",
    "b04-bolt-disc",
    "b08-unequal-angle",
    "b09-u-channel",
    "b10-stepped-pin",
    "b12-machine-base",
    "b13-standoff",
    "b15-nema23-plate",
    "b17-cup",
)
EPS = 1e-4
# probe lines run just off the symmetry planes, where triangulation diagonals cross
OFF_AXIS = np.array([0.0123, 0.0137, 0.0])
Array = NDArray[np.float64]


@dataclass(frozen=True)
class Outcome:
    case: Case
    design: Design | None
    artifact: Artifact | None
    results: list[CheckResult]
    seconds: float

    @property
    def valid(self) -> bool:
        return self.artifact is not None and self.artifact.ok

    @property
    def passed(self) -> bool:
        return self.valid and all(r.passed for r in self.results)

    def measured(self) -> dict[str, Value]:
        failed = "; ".join(f"{r.requirement.description}: {r.actual}" for r in self.results if not r.passed)
        checks = f"{sum(r.passed for r in self.results)}/{len(self.case.checks)}"
        return {"checks": checks, "valid": self.valid, "failed": failed, "seconds": self.seconds}


class BenchCase(BaseModel):
    id: str
    valid: bool
    checks_passed: int
    checks_total: int
    seconds: float
    param_accuracy: float | None
    hausdorff_mm: float | None


def part(case_id: str) -> Case:
    (case,) = [c for c in load_cases(PARTS) if c.id == case_id]
    return case


def family(prefix: str) -> list[Case]:
    return [c for c in load_cases(PARTS) if c.id.startswith(prefix)]


def run(rig: Rig, case: Case) -> Outcome:
    start, agent = time.monotonic(), rig.config.agent
    steps = list(generate(case.prompt, rig.llm, rig.geometry, rig.out / case.id, agent.max_repairs, agent.seed))
    (rig.out / f"{case.id}_steps.json").write_text(dump_steps(steps), encoding="utf-8")
    r = steps[-1].result
    art = r.artifact if r else None
    return Outcome(case, r.design if r else None, art, check(case.checks, art) if art else [], round(time.monotonic() - start, 1))


def checked(row: str, o: Outcome, extra: Measured | None = None, *more: bool, note: str = "") -> Evidence:
    return evidence(row, {**o.measured(), **(extra or {})}, o.passed, *more, note=note)


def sub(rig: Rig, name: str) -> Rig:
    (rig.out / name).mkdir(parents=True, exist_ok=True)
    return Rig(rig.out / name, rig.geometry, rig.llm, rig.config, rig.vision)


def near(value: float | None, target: float, tol: float) -> bool:
    return value is not None and abs(value - target) <= tol


def mesh(art: Artifact) -> trimesh.Trimesh:
    loaded: trimesh.Trimesh = trimesh.load_mesh(art.files["stl"], force="mesh")
    return loaded


def holes(art: Artifact, lo: float, hi: float) -> list[HoleInfo]:
    return [h for p in art.parts for h in p.holes if lo <= h.diameter <= hi]


def crossings(m: trimesh.Trimesh, p: Array, d: Array) -> list[float]:
    tri = m.triangles
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    h = np.cross(d, e2)
    a = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(a) > 1e-12
    f = np.divide(1.0, a, out=np.zeros_like(a), where=ok)
    s = p - tri[:, 0]
    u = f * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, e1)
    v = f * (q @ d)
    t = f * np.einsum("ij,ij->i", e2, q)
    hit = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
    ts: list[float] = []
    for x in sorted(t[hit].tolist()):
        if not ts or x - ts[-1] > 1e-6:  # a line through a shared edge hits both triangles
            ts.append(x)
    return ts


def intervals(m: trimesh.Trimesh, p: Array, d: Array) -> list[tuple[float, float]]:
    ts = crossings(m, p, d / np.linalg.norm(d))
    return list(zip(ts[::2], ts[1::2], strict=False))


def gap_at(runs: list[tuple[float, float]], t: float) -> float | None:
    return next((b[0] - a[1] for a, b in itertools.pairwise(runs) if a[1] <= t <= b[0]), None)


def levels(m: trimesh.Trimesh, axis: int) -> list[float]:
    zs = np.unique(np.round(m.vertices[:, axis], 4))
    return [float(a + b) / 2 for a, b in itertools.pairwise(zs)]


def unit(axis: int) -> Array:
    row: Array = np.eye(3)[axis]
    return row


def dp_1(rig: Rig) -> Evidence:
    o = run(rig, part("dp1-quad-frame"))
    motor = holes(o.artifact, 3.1, 3.6) if o.artifact else []
    pads = clusters([np.array(h.center) for h in motor], 25.0)
    centre = np.mean([c for c, _ in pads], axis=0) if pads else np.zeros(3)
    reach = [float(np.linalg.norm(c - centre)) for c, _ in pads]
    spread = max(reach) - min(reach) if reach else None
    m: Measured = {"motor_pads": len(pads), "holes_per_pad": ", ".join(str(n) for _, n in pads), "arm_reach_spread": spread}
    return checked("DP-1", o, m, len(pads) == 4, all(n == 4 for _, n in pads), near(spread, 0, 0.05))


def clusters(points: list[Array], link: float) -> list[tuple[Array, int]]:
    groups: list[list[Array]] = []
    for p in points:
        joined = [g for g in groups if any(np.linalg.norm(p - q) <= link for q in g)]
        merged = [p, *(q for g in joined for q in g)]
        groups = [g for g in groups if not any(g is j for j in joined)] + [merged]
    return [(np.mean(g, axis=0), len(g)) for g in groups]


def dp_3(rig: Rig) -> Evidence:
    return checked("DP-3", run(rig, part("dp3-dn50-pn16")))


def dp_4(rig: Rig) -> Evidence:
    o = run(rig, part("dp4-glider"))
    if not (o.design and o.artifact and o.valid):
        return checked("DP-4", o)
    agent = rig.config.agent
    r = list(refine(o.design, LONGER, rig.llm, rig.geometry, rig.out / "refine", agent.max_repairs, agent.seed))[-1].result
    if not (r and r.artifact and r.artifact.ok):
        return evidence("DP-4", {**o.measured(), "refined": False}, False)
    (l0, f0), (l1, f1) = fuselage(o.artifact), fuselage(r.artifact)
    m: Measured = {"length_before": l0, "length_after": l1, "fineness_before": f0, "fineness_after": f1}
    return evidence("DP-4", m, near(l1, 450, 0.5), f0 is not None and f1 is not None and f1 > f0)


def fuselage(art: Artifact) -> tuple[float | None, float | None]:
    body = next((p for p in art.parts if "fuselage" in p.name.lower()), None)
    if body is None:
        return None, None
    size = sorted(body.bbox_size)
    return round(size[2], 3), round(size[2] / size[1], 3)


def dp_6(rig: Rig) -> Evidence:
    o = run(rig, part("dp6-tee-plate"))
    if not (o.artifact and o.valid):
        return checked("DP-6", o)
    width, edges = leg_width(o.artifact), slot_offsets(o.artifact)
    m: Measured = {"leg_width": width, "hole_edge_offsets": ", ".join(f"{e:.3f}" for e in edges)}
    return checked("DP-6", o, m, near(width, 20, 0.05), bool(edges) and all(near(e, 10, 0.05) for e in edges))


def leg_width(art: Artifact) -> float | None:
    (p,) = art.parts
    t, a, b = sorted(p.bbox_size)
    area = (p.volume + sum(math.pi * h.diameter**2 / 4 * h.length for h in p.holes)) / t
    disc = (a + b) ** 2 - 4 * area
    return round(((a + b) - math.sqrt(disc)) / 2, 4) if disc >= 0 else None


def slot_offsets(art: Artifact) -> list[float]:
    m, (p,) = mesh(art), art.parts
    normal = int(np.argmin(p.bbox_size))
    return [min((e for k in range(3) if k != normal for e in edge_ends(m, h, k)), default=math.inf) for h in p.holes]


def edge_ends(m: trimesh.Trimesh, h: HoleInfo, axis: int) -> list[float]:
    runs = intervals(m, np.array(h.center), unit(axis))
    left, right = [r for r in runs if r[1] <= 0], [r for r in runs if r[0] >= 0]
    return ([-left[-1][0]] if left else []) + ([right[0][1]] if right else [])


def dp_8(rig: Rig) -> Evidence:
    o = run(rig, part("dp8-hose-connector"))
    found = hose(o.artifact) if o.artifact and o.valid else {}
    targets = {"barb_od": 16.0, "barb_length": 30.0, "bore": 12.0, "fitting_od": 26.4}
    ok = [near(v if isinstance(v, float) else None, targets[k], 0.05) for k, v in found.items() if k in targets]
    return checked("DP-8", o, found, len(ok) == len(targets), all(ok), found.get("bore_through") is True, found.get("hex") is True)


def hose(art: Artifact) -> dict[str, Value]:
    bores = holes(art, 11.95, 12.05)
    if not bores:
        return {}
    bore = max(bores, key=lambda h: h.length)
    m, axis, c = mesh(art), np.array(bore.axis), np.array(bore.center)
    t = (m.vertices - c) @ axis
    lo, hi = float(t.min()), float(t.max())
    if radius_at(m, c, axis, lo + EPS) > radius_at(m, c, axis, hi - EPS):
        axis, lo, hi = -axis, -hi, -lo
    cuts = np.unique(np.round((m.vertices - c) @ axis, 4))
    spans = [(float(a), float(b)) for a, b in itertools.pairwise(cuts)]
    barb_end, barb_r = lo, 0.0
    for a, b in spans:
        r = max(radius_at(m, c, axis, a + EPS), radius_at(m, c, axis, b - EPS))
        if r > 8.05:
            break
        barb_end, barb_r = b, max(barb_r, r)
    rest = [s for s in spans if s[0] >= barb_end]
    collar = [s for s in rest if hexagon(section(m, c + axis * (s[0] + s[1]) / 2, axis))]
    after = [s for s in rest if not collar or s[0] >= max(b for _, b in collar)]
    fitting = max(after, key=lambda s: s[1] - s[0], default=None)
    return {
        "barb_od": round(2 * barb_r, 4),
        "barb_length": round(barb_end - lo, 4),
        "bore": round(bore.diameter, 4),
        "bore_through": bore.length >= hi - lo - 0.05,
        "fitting_od": round(2 * radius_at(m, c, axis, (fitting[0] + fitting[1]) / 2), 4) if fitting else None,
        "hex": bool(collar),
    }


def section(m: trimesh.Trimesh, origin: Array, normal: Array) -> Array:
    segments: Array = trimesh.intersections.mesh_plane(m, normal, origin)
    return segments.reshape(-1, 3) - origin


def radius_at(m: trimesh.Trimesh, c: Array, axis: Array, t: float) -> float:
    pts = section(m, c + axis * t, axis)
    return float(np.linalg.norm(pts, axis=1).max()) if len(pts) else 0.0


def hexagon(pts: Array) -> bool:
    if len(pts) < 6:
        return False
    flat = pts @ np.linalg.svd(pts)[2][:2].T
    ring = flat[ConvexHull(flat).vertices]
    edges = np.roll(ring, -1, axis=0) - ring
    sides: list[Array] = []
    for e in edges:
        if sides and abs(sides[-1][0] * e[1] - sides[-1][1] * e[0]) <= 1e-3 * np.linalg.norm(sides[-1]) * np.linalg.norm(e):
            sides[-1] = sides[-1] + e
        else:
            sides.append(e)
    lengths = [float(np.linalg.norm(s)) for s in sides]
    radius = float(np.linalg.norm(flat, axis=1).max())
    long = [x for x in lengths if x > 0.3 * radius]
    return len(long) == 6 and max(long) - min(long) <= 0.05 * max(long)


def dp_11(rig: Rig) -> Evidence:
    o = run(rig, part("dp11-enclosure"))
    if not (o.design and o.artifact and o.valid and o.artifact.assembly):
        return checked("DP-11", o)
    screws = [p for p in o.artifact.parts if "screw" in p.name.lower()]
    tree = joint_tree(o.design)
    box = max((p for p in o.artifact.parts if p not in screws and "lid" not in p.name.lower()), key=lambda p: p.volume, default=None)
    bosses = [h for h in box.holes if h.diameter <= 3.4] if box else []
    seated = [s for s in screws if s.id in tree and any(on_axis(s.bbox_min, s.bbox_size, h) for h in bosses)]
    clearance = lid_clearance(mesh(o.artifact))
    m: Measured = {
        "screws": len(screws),
        "screws_mated_in_bosses": len(seated),
        "broken_mates": ", ".join(o.artifact.assembly.broken_mates()),
        "lid_clearance": ", ".join(f"{g:.3f}" for g in clearance or []),
    }
    fits = clearance is not None and all(near(g, 0.2, 0.02) for g in clearance)
    return checked("DP-11", o, m, len(screws) == 4, len(seated) == 4, not o.artifact.assembly.broken_mates(), fits)


def on_axis(lo: tuple[float, float, float], size: tuple[float, float, float], h: HoleInfo) -> bool:
    centre = np.array(lo) + np.array(size) / 2
    offset = centre - np.array(h.center)
    axis = np.array(h.axis) / np.linalg.norm(h.axis)
    return float(np.linalg.norm(offset - offset.dot(axis) * axis)) <= 0.05


def lid_clearance(m: trimesh.Trimesh) -> list[float] | None:
    lo, hi = m.bounds
    centre = (lo + hi) / 2 + OFF_AXIS
    best: list[float] | None = None
    for z in levels(m, 2):
        sides = []
        for k in (0, 1):
            runs = intervals(m, np.array([*centre[:2], z]) - unit(k) * 1e4, unit(k))
            if len(runs) >= 3:
                sides += [runs[1][0] - runs[0][1], runs[-1][0] - runs[-2][1]]
        if len(sides) == 4 and (best is None or max(sides) < max(best)):
            best = sides
    return best


def dp_12(rig: Rig) -> Evidence:
    ev = parity_m4_vision.in_5(rig)
    spacing = ev.measured.get("tab_hole_spacing")
    ok = isinstance(spacing, float) and near(spacing, SERVO_TAB_SPACING, 0.1)
    return ev.model_copy(update={"row": "DP-12", "passed": ev.passed and ok, "note": f"IN-5 plus tab holes {SERVO_TAB_SPACING} ±0.1"})


def dp_13(rig: Rig) -> Evidence:
    o = run(rig, part("dp13-fin-ray"))
    if not (o.design and o.valid):
        return checked("DP-13", o)
    plan = plan_variants(o.design, RIBS, rig.llm, rig.config.agent.seed)
    built = [rig.geometry.build(apply_params(o.design, {plan.param: v}), rig.out / f"ribs_{v:g}") for v in plan.values]
    ribs = [cells(mesh(a)) - 1 for a in built]  # n ribs split the closed finger into n + 1 cells
    length = max((p for p in o.design.params if p.unit == "mm"), key=lambda p: p.value)
    sweep = [apply_params(o.design, {length.name: length.value * (0.8 + 0.4 * i / 99)}) for i in range(100)]
    solids = sum(one_solid(rig, d) for d in sweep)
    m: Measured = {"variant_param": plan.param, "rib_counts": ", ".join(map(str, ribs)), "sweep_param": length.name, "sweep_valid": solids}
    return checked("DP-13", o, m, ribs == [4, 6, 8], all(a.ok for a in built), solids == 100)


def one_solid(rig: Rig, design: Design) -> bool:
    try:
        return all(p.valid and p.solids == 1 for p in rig.geometry.measure(design))
    except BuildError:
        return False


def cells(m: trimesh.Trimesh) -> int:
    lo, hi = m.bounds
    k = int(np.argmin(hi - lo))
    cut = m.section(plane_origin=(lo + hi) / 2, plane_normal=unit(k))
    return len(cut.discrete) - 1 if cut is not None else 0


def dp_14(rig: Rig, cases: list[Case] | None = None) -> Evidence:
    return run_family(rig, "DP-14", cases or family("dp14-"), gusset_check)


def gusset_check(o: Outcome) -> tuple[Measured, bool]:
    expected = GUSSETS.get(o.case.id)
    if expected is None:
        return {}, True
    found = gussets(o.design) if o.design else 0
    return {"gussets": found}, found == expected


def gussets(design: Design) -> int:
    values, total = design.param_values(), 0
    for p in design.parts:
        copies = {
            f: 2 if x.type == "mirror" else round(evaluate(x.count, values))
            for x in p.features
            if isinstance(x, Pattern)
            for f in x.features
        }
        sketches = {s.id: s for s in p.sketches}
        for f in p.features:
            if isinstance(f, Extrude) and f.mode == "add":
                total += sum(sloped(e, values) for e in sketches[f.sketch].entities) * copies.get(f.id, 1)
    return total


def sloped(entity: object, values: dict[str, float]) -> bool:
    if isinstance(entity, Polygon):
        corners = list(entity.points)
    elif isinstance(entity, SketchPath):
        corners = [entity.start, *(s.to for s in entity.segments)]
    else:
        return False
    xy = [(evaluate(x, values), evaluate(y, values)) for x, y in corners]
    return any(abs(b[0] - a[0]) > 1e-6 and abs(b[1] - a[1]) > 1e-6 for a, b in zip(xy, xy[1:] + xy[:1], strict=True))


def dp_15(rig: Rig, cases: list[Case] | None = None) -> Evidence:
    return run_family(rig, "DP-15", cases or family("dp15-"))


def dp_18(rig: Rig, cases: list[Case] | None = None) -> Evidence:
    return run_family(rig, "DP-18", cases or family("dp18-"))


def dp_20(rig: Rig, cases: list[Case] | None = None) -> Evidence:
    return run_family(rig, "DP-20", cases or family("dp20-"), fixture_check)


def fixture_check(o: Outcome) -> tuple[Measured, bool]:
    if not (o.artifact and o.design):
        return {}, False
    if o.case.id == "dp20-two-link-arm":
        pockets = servo_pockets(o.artifact)
        revolute = bool(o.design.assembly and any(j.kind == "revolute" for j in o.design.assembly.joints))
        fit = len(pockets) == 2 and all(22.75 <= p <= 23.3 for p in pockets)
        return {"links": len(o.design.parts), "revolute": revolute, "pockets": str(pockets)}, len(o.design.parts) >= 2 and revolute and fit
    if o.case.id == "dp20-drill-jig":
        pocket = jig_pocket(mesh(o.artifact), 3.0)
        return {"pocket": str(pocket)}, near(pocket[0], 110.4, 0.1) and near(pocket[1], 80.4, 0.1)
    return {}, True


def servo_pockets(art: Artifact) -> list[float]:
    m, tabs = mesh(art), holes(art, 1.9, 2.2)
    found = []
    for i, a in enumerate(tabs):
        for b in tabs[i + 1 :]:
            d = np.array(b.center) - np.array(a.center)
            dist = float(np.linalg.norm(d))
            if near(dist, SERVO_TAB_SPACING, 0.1):
                gap = gap_at(intervals(m, np.array(a.center) - d / dist * 1e3, d), 1e3 + dist / 2)
                found += [round(gap, 3)] if gap is not None else []
    return found


def jig_pocket(m: trimesh.Trimesh, depth: float) -> tuple[float | None, float | None]:
    lo, hi = m.bounds
    centre = (lo + hi) / 2 + OFF_AXIS
    centre[2] = hi[2] - depth
    x, y = (gap_at(intervals(m, centre - unit(k) * 1e4, unit(k)), 1e4) for k in (0, 1))
    return x, y


def run_family(rig: Rig, row: str, cases: list[Case], extra: Callable[[Outcome], tuple[Measured, bool]] | None = None) -> Evidence:
    results = []
    for case in cases:
        o = run(rig, case)
        measured, ok = extra(o) if extra else ({}, True)
        results.append({"id": case.id, **o.measured(), **measured, "passed": o.passed and ok})
    (rig.out / "cases.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    failed = [str(r["id"]) for r in results if not r["passed"]]
    m: Measured = {"cases": len(cases), "passed": len(cases) - len(failed), "failed": ", ".join(failed)}
    return evidence(row, m, not failed, note="per-case checks in cases.json")


def dp_16(rig: Rig) -> Evidence:
    parts = [parity_m4_assembly.ge_6(sub(rig, "GE-6")), parity_m4_assembly.pr_8(sub(rig, "PR-8"))]
    m: Measured = {f"{e.row}_{k}": v for e in parts for k, v in e.measured.items()}
    return evidence("DP-16", m, *(e.passed for e in parts), note="GE-6 (generated drone) and PR-8 (battery mount moved for CoG)")


def dp_19(rig: Rig) -> Evidence:
    o = run(rig, part("dp19-phone-holder"))
    if not (o.design and o.artifact and o.valid):
        return checked("DP-19", o)
    width = next((p.name for p in o.design.params if p.value == 75), None)
    if width is None:
        return checked("DP-19", o, {"phone_width_param": None}, False)
    edited = rig.geometry.build(apply_params(o.design, {width: 70}), rig.out / "phone-70")
    before, after = cradle(mesh(o.artifact), 75.5), cradle(mesh(edited), 70.5)
    m: Measured = {"phone_width_param": width, "inner_width_75": before, "inner_width_70": after, "edited_valid": edited.ok}
    return checked("DP-19", o, m, near(before, 75.5, 0.05), near(after, 70.5, 0.05), edited.ok)


def cradle(m: trimesh.Trimesh, target: float) -> float | None:
    lo, hi = m.bounds
    centre = (lo + hi) / 2 + OFF_AXIS
    found: list[float] = []
    for z in levels(m, 2):
        for k in (0, 1):
            runs = intervals(m, np.array([*centre[:2], z]) - unit(k) * 1e4, unit(k))
            found += [b[0] - a[1] for a, b in itertools.pairwise(runs)]
    if not found:
        return None
    best: float = min(found, key=lambda g: abs(g - target))
    return round(best, 4)


def dp_22(rig: Rig) -> Evidence:
    return checked("DP-22", run(rig, part("dp22-naca-intake")))


def reference(case_id: str) -> Design:
    return Design.model_validate_json((FIXTURES / "reference" / f"{case_id}.json").read_text(encoding="utf-8"))


def bench(rig: Rig) -> list[BenchCase]:
    # GE-8, VM-8, PF-1 and PF-7 read one pass over the benchmark in the same parity run
    cache = rig.out.parent / "benchmark.json"
    if cache.exists():
        return [BenchCase.model_validate(c) for c in json.loads(cache.read_text(encoding="utf-8"))]
    out = rig.out.parent / "benchmark"
    out.mkdir(parents=True, exist_ok=True)
    shared = Rig(out, rig.geometry, rig.llm, rig.config, rig.vision)
    results = [bench_case(shared, c) for c in load_cases(BENCHMARK)]
    cache.write_text(json.dumps([r.model_dump() for r in results], indent=2), encoding="utf-8")
    return results


def bench_case(rig: Rig, case: Case) -> BenchCase:
    o, ref = run(rig, case), reference(case.id)
    accuracy = param_accuracy(ref, o.design) if o.design else None
    distance = None
    if o.artifact:
        ref_art = rig.geometry.build(ref, rig.out / case.id / "reference")
        distance = aligned_hausdorff(ref_art.files["stl"], o.artifact.files["stl"], rig.out / case.id)
    return BenchCase(
        id=case.id,
        valid=o.valid,
        checks_passed=sum(r.passed for r in o.results),
        checks_total=len(case.checks),
        seconds=o.seconds,
        param_accuracy=accuracy,
        hausdorff_mm=distance,
    )


def param_accuracy(ref: Design, got: Design) -> float:
    return round(matched([p.value for p in ref.params], [p.value for p in got.params], 0.01) / len(ref.params), 4)


def matched(truth: list[float], values: list[float], rel: float) -> int:
    free, hits = list(values), 0
    for t in truth:
        best = min(free, key=lambda v: abs(v - t), default=None)
        if best is not None and abs(best - t) <= max(rel * abs(t), 1e-6):
            free.remove(best)
            hits += 1
    return hits


def rotations() -> list[Array]:
    out = []
    for perm in ([0, 1, 2], [1, 2, 0], [2, 0, 1], [0, 2, 1], [2, 1, 0], [1, 0, 2]):
        for signs in np.array(np.meshgrid([1, -1], [1, -1], [1, -1])).T.reshape(-1, 3):
            r = np.eye(3)[perm] * signs[:, None]
            if np.linalg.det(r) > 0:
                out.append(r)
    return out


def aligned_hausdorff(ref_stl: Path, got_stl: Path, out: Path) -> float:
    ref, got = trimesh.load_mesh(ref_stl, force="mesh"), trimesh.load_mesh(got_stl, force="mesh")
    ref_mid, got_mid = ref.bounds.mean(axis=0), got.bounds.mean(axis=0)
    turns = sorted(rotations(), key=lambda r: float(np.abs(np.abs(r @ got.extents) - ref.extents).max()))
    best = math.inf
    for i, r in enumerate(turns[:4]):
        moved = got.copy()
        moved.vertices = (moved.vertices - got_mid) @ r.T + ref_mid
        path = out / f"aligned_{i}.stl"
        moved.export(path)
        best = min(best, hausdorff(ref_stl, path))
        if best <= 1e-3:
            break
    return round(best, 4)


def ge_8(rig: Rig) -> Evidence:
    results = bench(rig)
    passed, total = sum(r.checks_passed for r in results), sum(r.checks_total for r in results)
    share = passed / total if total else 0.0
    m: Measured = {"parts": len(results), "dims_within_tolerance": f"{passed}/{total}", "share": round(share, 4)}
    return evidence("GE-8", m, len(results) >= 30, share >= 0.95, note="dims of parts that failed to build count as missed")


def vm_8(rig: Rig) -> Evidence:
    cases, results = load_cases(BENCHMARK), bench(rig)
    refs = [(c, rig.geometry.build(reference(c.id), rig.out / c.id)) for c in cases]
    self_checked = [c.id for c, a in refs if not (a.ok and all(r.passed for r in check(c.checks, a)))]
    scored = [r for r in results if r.param_accuracy is not None and r.hausdorff_mm is not None]
    m: Measured = {
        "reference_parts": len(refs),
        "references_failing_spec": ", ".join(self_checked),
        "cases_scored": f"{len(scored)}/{len(results)}",
        "mean_param_accuracy": round(statistics.mean(r.param_accuracy or 0.0 for r in results), 4) if results else None,
        "median_hausdorff_mm": statistics.median(r.hausdorff_mm for r in scored if r.hausdorff_mm is not None) if scored else None,
    }
    note = "per-case param accuracy and Hausdorff in ../benchmark.json; a case whose generation did not build has no Hausdorff"
    return evidence("VM-8", m, len(refs) >= 30, not self_checked, len(results) == len(cases), note=note)


def ge_11(rig: Rig) -> Evidence:
    truth: dict[str, dict[str, float]] = json.loads((FIXTURES / "vision" / "truth.json").read_text(encoding="utf-8"))
    per: dict[str, Value] = {}
    hits = total = 0
    for name, values in truth.items():
        design, art = parity_m4_vision.design_from(rig, DRAWING, (FIXTURES / "vision" / f"{name}.png").read_bytes(), name)
        found = matched(list(values.values()), [p.value for p in design.params], 0.02) if design and art else 0
        per[name] = f"{found}/{len(values)}"
        hits, total = hits + found, total + len(values)
    share = hits / total
    return evidence("GE-11", {**per, "recovered": f"{hits}/{total}", "share": round(share, 4)}, share >= 0.9)


def pf_1(rig: Rig) -> Evidence:
    seconds = [r.seconds for r in bench(rig)]
    median = statistics.median(seconds)
    m: Measured = {"cases": len(seconds), "median_s": median, "max_s": max(seconds)}
    return evidence("PF-1", m, median <= 300, note="measured on this machine, not the reference laptop of docs/HARDWARE.md")


def pf_3(rig: Rig) -> Evidence:
    m: dict[str, Value] = {}
    ok = []
    for row, demo in (("IN-5", parity_m4_vision.in_5), ("IN-6", parity_m4_vision.in_6)):
        start = time.monotonic()
        ev = demo(sub(rig, row))
        seconds = round(time.monotonic() - start, 1)
        built = ev.measured.get("built") is not False
        m |= {f"{row}_seconds": seconds, f"{row}_built": built, f"{row}_passed": ev.passed}
        ok.append(built and seconds < 60)
    return evidence("PF-3", m, *ok, note="time to a built model; accuracy is gated by IN-5 and IN-6")


def pf_7(rig: Rig) -> Evidence:
    p50 = statistics.median(r.seconds for r in bench(rig))
    met = "met" if p50 < SECONDS_CLAIM else "not met"
    note = f"single-part benchmark prompts; the 'seconds' claim (p50 under {SECONDS_CLAIM:g} s) is {met}"
    return evidence("PF-7", {"p50_s": p50, "seconds_claim": met}, True, note=note)


def ollama_stats(host: str, model: str) -> tuple[int, int, int]:
    client = Client(host=host)
    reply = client.generate(model=model, prompt="List ten standard metric screw sizes.", options={"seed": 0, "num_predict": 256})
    size = next((m.size or 0 for m in client.ps().models if m.model == model), 0)
    return reply.eval_count or 0, reply.eval_duration or 0, size


def pf_8(rig: Rig) -> Evidence:
    tokens, nanos, size = ollama_stats(rig.config.llm.host, rig.llm.name)
    rate = tokens / (nanos / 1e9) if nanos else 0.0
    gib = size / 2**30
    m: Measured = {"model": rig.llm.name, "eval_tokens": tokens, "tokens_per_s": round(rate, 1), "loaded_size_gib": round(gib, 2)}
    return evidence("PF-8", m, 0 < gib <= 16, rate >= 10, note="Ollama eval counters on this machine, not the reference laptop")


def loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


@contextmanager
def offline() -> Iterator[list[str]]:
    blocked: list[str] = []
    connect, resolve = socket.socket.connect, socket.getaddrinfo

    def guarded_connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and not loopback(str(address[0])):
            blocked.append(str(address[0]))
            raise OSError(f"network disabled: {address[0]}")
        connect(self, address)

    def guarded_resolve(host: Any, *args: Any, **kwargs: Any) -> Any:
        if host is not None and not loopback(str(host)):
            blocked.append(str(host))
            raise OSError(f"network disabled: {host}")
        return resolve(host, *args, **kwargs)

    socket.socket.connect = guarded_connect  # type: ignore[method-assign,assignment]
    socket.getaddrinfo = guarded_resolve
    try:
        yield blocked
    finally:
        socket.socket.connect = connect  # type: ignore[method-assign]
        socket.getaddrinfo = resolve


def wp_15(rig: Rig) -> Evidence:
    cases = [c for c in load_cases(BENCHMARK) if c.id in OFFLINE]
    with offline() as blocked, serve(rig, rig.llm) as api:
        project = api.project()
        jobs = [api.generate(project, c.prompt) for c in cases]
    done = [j for j in jobs if j["status"] == "done"]
    host = rig.config.llm.host.split("//")[-1].split(":")[0]
    errors = "; ".join(f"{c.id}: {j.get('error')}" for c, j in zip(cases, jobs, strict=True) if j["status"] != "done")
    m: Measured = {"prompts": len(jobs), "completed": len(done), "errors": errors[:600], "blocked": ", ".join(blocked), "model_host": host}
    note = "outbound sockets and name lookups to anything but loopback raise inside the run"
    return evidence("WP-15", m, len(done) == len(OFFLINE), not blocked, loopback(host), note=note)


ROWS: dict[str, Demo] = {
    "DP-1": dp_1,
    "DP-3": dp_3,
    "DP-4": dp_4,
    "DP-6": dp_6,
    "DP-8": dp_8,
    "DP-11": dp_11,
    "DP-12": dp_12,
    "DP-13": dp_13,
    "DP-14": dp_14,
    "DP-15": dp_15,
    "DP-16": dp_16,
    "DP-18": dp_18,
    "DP-19": dp_19,
    "DP-20": dp_20,
    "DP-22": dp_22,
    "GE-8": ge_8,
    "GE-11": ge_11,
    "VM-8": vm_8,
    "PF-1": pf_1,
    "PF-3": pf_3,
    "PF-7": pf_7,
    "PF-8": pf_8,
    "WP-15": wp_15,
}
