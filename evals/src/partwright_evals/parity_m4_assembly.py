import math
import re
from collections.abc import Iterator
from pathlib import Path

from partwright_agent import Step, generate, place, refine
from partwright_evals.parity import Demo, Evidence, Measured, Rig, evidence
from partwright_geometry import Artifact, PartMetrics, Placement
from partwright_ir import Design, apply_params, joint_tree, part_hash
from partwright_ir.model import Extrude

FIXTURES = Path(__file__).parents[2] / "parity" / "m4" / "assembly"
DRONE_BRIEF = "Quadcopter: a centre frame plate, 4 arms, a motor mount at the end of each arm and a battery mount on the frame"
ENCLOSURE_BRIEF = "enclosure with lid and 4 M3 screws"
SERVO_BRIEF = "Micro servo, 22.5 x 12.2 mm body, with a mounting flange"
VENTS = "add vent slots"
EXACT = 1e-6
DENSITY = {"6061 aluminium": 2.70, "PETG": 1.27}
KINDS = {"frame": "frame", "arm": "arm", "motor": "motor", "battery": "battery"}
M3_CLEARANCE = 3.4  # ISO 273 normal fit
Vec = tuple[float, float, float]


def fixture(name: str) -> Design:
    return Design.model_validate_json((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def build(rig: Rig, design: Design, name: str) -> Artifact:
    return rig.geometry.build(design, rig.out / name)


def outcome(steps: Iterator[Step]) -> tuple[Design | None, Artifact | None]:
    r = list(steps)[-1].result
    return (r.design, r.artifact) if r else (None, None)


def hand_mass(v: dict[str, float]) -> tuple[float, Vec]:
    t, length, width, a = v["frame_thickness"], v["frame_length"], v["frame_width"], v["arm_length"]
    bt, mt = v["battery_thickness"], v["motor_mount_thickness"]
    hole = math.pi * (M3_CLEARANCE / 2) ** 2
    bolts = [(v["battery_x"] + sx * v["battery_hole_dx"] / 2, sy * v["battery_hole_dy"] / 2) for sx in (-1, 1) for sy in (-1, 1)]
    sides = [(1, 0, length / 2), (-1, 0, length / 2), (0, 1, width / 2), (0, -1, width / 2)]
    disc = math.pi * ((v["motor_mount_diameter"] / 2) ** 2 - (v["motor_bore"] / 2) ** 2) * mt
    alu, petg = DENSITY["6061 aluminium"], DENSITY["PETG"]
    bodies: list[tuple[float, Vec]] = [(alu * length * width * t, (0, 0, t / 2))]
    bodies += [(-alu * hole * t, (x, y, t / 2)) for x, y in bolts]
    bodies += [(alu * a * v["arm_width"] * t, (dx * (e + a / 2), dy * (e + a / 2), t / 2)) for dx, dy, e in sides]
    reach = [(dx * (e + a - v["motor_inset"]), dy * (e + a - v["motor_inset"])) for dx, dy, e in sides]
    bodies += [(petg * disc, (x, y, t + mt / 2)) for x, y in reach]
    bodies += [(alu * v["battery_length"] * v["battery_width"] * bt, (v["battery_x"], 0, t + bt / 2))]
    bodies += [(-alu * hole * bt, (x, y, t + bt / 2)) for x, y in bolts]
    milligrams = sum(m for m, _ in bodies)
    cog = tuple(sum(m * c[i] for m, c in bodies) / milligrams for i in range(3))
    return milligrams / 1000, (cog[0], cog[1], cog[2])


def _named(art: Artifact, pid: str) -> PartMetrics:
    return next(p for p in art.parts if p.id == pid)


def _hole_xy(p: PartMetrics) -> list[tuple[float, float]]:
    return sorted((round(h.center[0], 6), round(h.center[1], 6)) for h in p.holes if abs(h.diameter - M3_CLEARANCE) < 1e-6)


def _flat(p: Placement | None) -> list[float]:
    return [x for row in p or () for x in row]


def _drift(a: list[PartMetrics], b: list[PartMetrics]) -> float:
    return max(abs(x - y) for pa, pb in zip(a, b, strict=True) for x, y in zip(_flat(pa.placement), _flat(pb.placement), strict=True))


def as_2(rig: Rig) -> Evidence:
    design = fixture("drone")
    art = build(rig, design, "export")
    reloaded = Design.model_validate_json(art.files["ir"].read_text(encoding="utf-8"))
    rebuilt = build(rig, reloaded, "reloaded")
    step_parts = rig.geometry.import_step(art.files["step"])
    occurrences = art.files["step"].read_text(encoding="utf-8", errors="replace").count("NEXT_ASSEMBLY_USAGE_OCCURRENCE")
    mates = len(reloaded.assembly.joints) if reloaded.assembly else 0
    ir_drift, step_drift = _drift(art.parts, rebuilt.parts), _drift(art.parts, step_parts)
    m: Measured = {
        "mates_in_ir": mates,
        "step_components": occurrences,
        "ir_reload_error": ir_drift,
        "step_reload_error": step_drift,
    }
    return evidence(
        "AS-2",
        m,
        reloaded.assembly == design.assembly,
        mates == len(design.parts) - 1,
        occurrences == len(design.parts) == len(step_parts),
        ir_drift <= EXACT,
        step_drift <= EXACT,
        note="mates travel in our IR bundle; STEP carries the product structure and placements",
    )


def as_4(rig: Rig) -> Evidence:
    design = fixture("drone")
    report = build(rig, design, "build").assembly
    grams, cog = hand_mass(design.param_values())
    if report is None or report.mass_g is None or report.center_of_mass is None:
        return evidence("AS-4", {"reported": False}, False)
    mass_err = abs(report.mass_g - grams) / grams
    cog_err = math.dist(report.center_of_mass, cog) / math.hypot(*cog)
    m: Measured = {
        "mass_g": round(report.mass_g, 4),
        "hand_mass_g": round(grams, 4),
        "mass_error_pct": 100 * mass_err,
        "cog": str(tuple(round(c, 4) for c in report.center_of_mass)),
        "hand_cog": str(tuple(round(c, 4) for c in cog)),
        "cog_error_pct": 100 * cog_err,
    }
    return evidence("AS-4", m, mass_err <= 0.01, cog_err <= 0.01, note="CoG error relative to the hand-calculated CoG distance")


def pr_8(rig: Rig) -> Evidence:
    design = fixture("drone")
    moved = apply_params(design, {"battery_x": design.param_values()["battery_x"] - 20})
    before, after = build(rig, design, "before"), build(rig, moved, "after")
    if not (before.assembly and after.assembly and before.assembly.center_of_mass and after.assembly.center_of_mass):
        return evidence("PR-8", {"reported": False}, False)
    shift = [b - a for a, b in zip(before.assembly.center_of_mass, after.assembly.center_of_mass, strict=True)]
    predicted = [b - a for a, b in zip(hand_mass(design.param_values())[1], hand_mass(moved.param_values())[1], strict=True)]
    frame_before, frame_after = _hole_xy(_named(before, "frame")), _hole_xy(_named(after, "frame"))
    hole_moves = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(frame_before, frame_after, strict=True)]
    aligned = _hole_xy(_named(after, "battery_mount")) == frame_after
    broken = after.assembly.broken_mates()
    m: Measured = {
        "cog_shift_x": round(shift[0], 4),
        "predicted_shift_x": round(predicted[0], 4),
        "shift_error_mm": math.dist(shift, predicted),
        "frame_hole_moves_x": ", ".join(f"{dx:g}" for dx, _ in hole_moves),
        "holes_aligned": aligned,
        "broken_mates": ", ".join(broken),
    }
    moved_together = len(hole_moves) == 4 and all(abs(dx + 20) <= EXACT and abs(dy) <= EXACT for dx, dy in hole_moves)
    return evidence("PR-8", m, math.dist(shift, predicted) <= 1, moved_together, aligned, not broken, after.ok)


def ge_6(rig: Rig) -> Evidence:
    design, art = outcome(generate(DRONE_BRIEF, rig.llm, rig.geometry, rig.out / "gen", rig.config.agent.max_repairs))
    if not (design and art and art.assembly):
        return evidence("GE-6", {"built": False}, False)
    names = [p.name.lower() for p in design.parts]
    counts = {k: sum(bool(re.search(rx, n)) for n in names) for k, rx in KINDS.items()}
    report = art.assembly
    m: Measured = {
        **counts,
        "mass_g": report.mass_g and round(report.mass_g, 3),
        "cog": report.center_of_mass and str(tuple(round(c, 3) for c in report.center_of_mass)),
        "valid": art.ok,
    }
    return evidence(
        "GE-6",
        m,
        counts == {"frame": 1, "arm": 4, "motor": 4, "battery": 1},
        report.mass_g is not None,
        report.center_of_mass is not None,
        art.ok,
    )


def ge_5(rig: Rig) -> Evidence:
    design, art = outcome(generate(ENCLOSURE_BRIEF, rig.llm, rig.geometry, rig.out / "gen", rig.config.agent.max_repairs))
    if not (design and art and art.assembly):
        return evidence("GE-5", {"built": False}, False)
    tree = joint_tree(design)
    parents = {parent for _, parent in tree.values()}
    unmated = [p.id for p in design.parts if p.id not in tree and p.id not in parents]
    screws = sum("screw" in p.name.lower() for p in design.parts)
    worst = max((i.volume for i in art.assembly.interferences), default=0.0)
    m: Measured = {
        "components": len(design.parts),
        "screws": screws,
        "unmated": ", ".join(unmated),
        "pairs_in_contact": len(art.assembly.interferences),
        "max_interference_mm3": worst,
        "broken_mates": ", ".join(art.assembly.broken_mates()),
    }
    return evidence("GE-5", m, len(design.parts) >= 6, screws == 4, not unmated, worst <= EXACT, not art.assembly.broken_mates(), art.ok)


def pr_5(rig: Rig) -> Evidence:
    design = fixture("enclosure")
    before = build(rig, design, "before")
    edited, art = outcome(refine(design, VENTS, rig.llm, rig.geometry, rig.out / "edit", rig.config.agent.max_repairs, target="lid"))
    if not (edited and art):
        return evidence("PR-5", {"built": False}, False)
    old_lid = next(p for p in design.parts if p.id == "lid")
    new_lid = next(p for p in edited.parts if p.id == "lid")
    sketches = {s.id: s for s in new_lid.sketches}
    added = [f for f in new_lid.features if f not in old_lid.features]
    cuts = [f for f in added if isinstance(f, Extrude) and f.mode == "cut"]
    slots = [f.id for f in cuts if any(e.kind == "slot" for e in sketches[f.sketch].entities)]
    others = [p.id for p in design.parts if p.id != "lid" and part_hash(edited, p.id) != part_hash(design, p.id)]
    removed = _named(before, "lid").volume - _named(art, "lid").volume
    m: Measured = {
        "base_hash_before": part_hash(design, "base"),
        "base_hash_after": part_hash(edited, "base"),
        "other_components_changed": ", ".join(others),
        "slot_features": ", ".join(slots),
        "lid_volume_removed_mm3": round(removed, 3),
        "valid": art.ok,
    }
    return evidence("PR-5", m, not others, bool(slots), removed > 0, art.ok)


def as_3(rig: Rig) -> Evidence:
    target = fixture("servo_mount")
    steps = place(SERVO_BRIEF, target, "servo_pocket", rig.llm, rig.geometry, rig.out / "place", rig.config.agent.max_repairs)
    design, art = outcome(steps)
    if not (design and art and art.assembly and design.assembly):
        return evidence("AS-3", {"built": False}, False)
    new = [p.id for p in design.parts if p.id not in {q.id for q in target.parts}]
    mated = [j.id for j in design.assembly.joints if j.parent == "servo_pocket"]
    worst = max((i.volume for i in art.assembly.interferences), default=0.0)
    m: Measured = {
        "new_part": ", ".join(new),
        "mate": ", ".join(mated),
        "max_interference_mm3": worst,
        "broken_mates": ", ".join(art.assembly.broken_mates()),
        "valid": art.ok,
    }
    return evidence("AS-3", m, len(new) == 1, len(mated) == 1, worst <= EXACT, not art.assembly.broken_mates(), art.ok)


ROWS: dict[str, Demo] = {
    "AS-2": as_2,
    "AS-3": as_3,
    "AS-4": as_4,
    "GE-5": ge_5,
    "GE-6": ge_6,
    "PR-5": pr_5,
    "PR-8": pr_8,
}
