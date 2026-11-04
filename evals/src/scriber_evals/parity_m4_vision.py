import io
import json
from pathlib import Path

import numpy as np
import pypdfium2
import trimesh

from scriber_agent import LLM, critique, dump_steps, generate
from scriber_cli.config import llm_for
from scriber_context import document_text
from scriber_evals.parity import Demo, Evidence, Measured, Rig, evidence
from scriber_geometry import Artifact, HoleInfo
from scriber_ir import Design, Param

FIXTURES = Path(__file__).parents[2] / "parity" / "m4" / "vision"
SKETCH = "Model the L-bracket in the attached hand-drawn sketch."
SERVO = "Model the 9 g hobby servo in the attached photo as one solid part, using these datasheet dimensions:\n\n{datasheet}"
DRAWING = "Model the flange in the attached technical drawing. The text on the drawing reads:\n\n{text}"
SERVO_LWH = (32.2, 11.8, 26.7)
FLANGE = {"od": 120.0, "pcd": 90.0, "hole_d": 11.0, "hub_d": 60.0}
# the thumbnail camera looks along this glTF direction; turning the part's +Z onto it gives a plan view
CAMERA = (1.0, 0.9, 1.2)


def vision_llm(rig: Rig) -> LLM:
    return llm_for(rig.config, rig.config.llm.vision)


def design_from(rig: Rig, prompt: str, image: bytes, name: str) -> tuple[Design | None, Artifact | None]:
    agent, vision = rig.config.agent, vision_llm(rig)
    steps = list(generate(prompt, rig.llm, rig.geometry, rig.out / name, agent.max_repairs, agent.seed, images=(image,), vision=vision))
    (rig.out / f"{name}_steps.json").write_text(dump_steps(steps), encoding="utf-8")
    r = steps[-1].result
    return (r.design, r.artifact) if r else (None, None)


def named(design: Design, key: str, target: float) -> float | None:
    values = [p.value for p in design.params if key in p.name]
    return min(values, key=lambda v: abs(v - target)) if values else None


def near(value: float | None, target: float, tol: float) -> bool:
    return value is not None and abs(value - target) <= tol


def bounds(art: Artifact) -> tuple[np.ndarray, np.ndarray]:
    lo: np.ndarray = np.min([p.bbox_min for p in art.parts], axis=0)
    hi: np.ndarray = np.max([np.add(p.bbox_min, p.bbox_size) for p in art.parts], axis=0)
    return lo, hi


def extents(art: Artifact) -> list[float]:
    lo, hi = bounds(art)
    return sorted(round(float(v), 3) for v in hi - lo)


def holes(art: Artifact) -> list[HoleInfo]:
    return [h for p in art.parts for h in p.holes]


def in_4(rig: Rig) -> Evidence:
    design, art = design_from(rig, SKETCH, (FIXTURES / "l_bracket_sketch.png").read_bytes(), "sketch")
    if not (design and art):
        return evidence("IN-4", {"built": False}, False)
    targets = {"length": 120.0, "width": 40.0, "thick": 4.0}
    found = {key: named(design, key, t) for key, t in targets.items()}
    found_holes = holes(art)
    m: Measured = {**found, "holes": len(found_holes), "hole_d": ", ".join(f"{h.diameter:.2f}" for h in found_holes), "valid": art.ok}
    return evidence("IN-4", m, art.ok, len(found_holes) == 2, *(near(found[k], t, 0.02 * t) for k, t in targets.items()))


def in_5(rig: Rig) -> Evidence:
    datasheet = (FIXTURES / "servo_datasheet.md").read_text(encoding="utf-8")
    design, art = design_from(rig, SERVO.format(datasheet=datasheet), (FIXTURES / "servo.png").read_bytes(), "servo")
    if not (design and art):
        return evidence("IN-5", {"built": False}, False)
    size, expected = extents(art), sorted(SERVO_LWH)
    within = [abs(a - e) <= 0.1 * e for a, e in zip(size, expected, strict=True)]
    m: Measured = {"bbox_sorted": str(size), "datasheet_sorted": str(expected), "params": len(design.params), "valid": art.ok}
    m = {**m, "tab_hole_spacing": tab_spacing(art)}
    return evidence("IN-5", m, art.ok, all(within), len(design.params) >= 5, note="tab_hole_spacing is DP-12's measure, not gated here")


def tab_spacing(art: Artifact) -> float | None:
    small = [np.array(h.center) for h in holes(art) if h.diameter <= 3]
    return round(float(np.linalg.norm(small[0] - small[1])), 3) if len(small) == 2 else None


def in_6(rig: Rig) -> Evidence:
    pdf = FIXTURES / "flange_drawing.pdf"
    prompt = DRAWING.format(text=document_text(pdf))
    design, art = design_from(rig, prompt, page_png(pdf), "flange")
    if not (design and art):
        return evidence("IN-6", {"built": False}, False)
    params = {key: closest(design, t) for key, t in FLANGE.items()}
    bolts = [h for h in holes(art) if near(h.diameter, FLANGE["hole_d"], 0.1)]
    radii = [round(radius(h, art), 3) for h in bolts]
    size = extents(art)
    m: Measured = {
        **{f"param_{k}": f"{p.name}={p.value:g}" if p else None for k, p in params.items()},
        "bolt_holes": len(bolts),
        "bolt_radii": ", ".join(map(str, radii)),
        "od": size[-1],
        "valid": art.ok,
    }
    checks = [near(p.value if p else None, FLANGE[k], 0.1) for k, p in params.items()]
    built = [len(bolts) == 6, all(near(r, FLANGE["pcd"] / 2, 0.1) for r in radii), near(size[-1], 120, 0.1), near(size[-2], 120, 0.1)]
    return evidence("IN-6", m, art.ok, *checks, *built)


def closest(design: Design, target: float) -> Param | None:
    return min(design.params, key=lambda p: abs(p.value - target), default=None)


def page_png(pdf: Path) -> bytes:
    doc = pypdfium2.PdfDocument(pdf)
    try:
        image = doc[0].render(scale=2).to_pil()
    finally:
        doc.close()
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def radius(h: HoleInfo, art: Artifact) -> float:
    lo, hi = bounds(art)
    offset = np.array(h.center) - (lo + hi) / 2
    axis = np.array(h.axis) / np.linalg.norm(h.axis)
    return float(np.linalg.norm(offset - offset.dot(axis) * axis))


def vm_10(rig: Rig) -> Evidence:
    cases = json.loads((FIXTURES / "critic_cases.json").read_text(encoding="utf-8"))
    vision, verdicts = vision_llm(rig), []
    for i, case in enumerate(cases):
        right = Design.model_validate(case["design"])
        for kind, design in (("right", right), ("wrong", missing_hole(right))):
            name = f"case{i}_{kind}"
            verdict = critique(case["request"], views(rig, rig.geometry.build(design, rig.out / name), name), vision, rig.config.agent.seed)
            verdicts.append({"case": i, "kind": kind, **verdict.model_dump(mode="json")})
    (rig.out / "verdicts.json").write_text(json.dumps(verdicts, indent=2), encoding="utf-8")
    flagged = sum(not v["matches"] for v in verdicts if v["kind"] == "wrong")
    false_flags = sum(not v["matches"] for v in verdicts if v["kind"] == "right")
    m: Measured = {"wrong_flagged": f"{flagged}/{len(cases)}", "right_flagged": f"{false_flags}/{len(cases)}"}
    note = "control: the correct parts must pass too, or a critic that rejects everything would meet the row"
    return evidence("VM-10", m, flagged >= 4, false_flags <= 1, note=note)


def missing_hole(design: Design) -> Design:
    data = design.model_dump(mode="json")
    (hole,) = [f for f in data["parts"][0]["features"] if f["kind"] == "hole"]
    hole["at"]["points"].pop()
    return Design.model_validate(data)


def views(rig: Rig, art: Artifact, name: str) -> list[bytes]:
    scene = trimesh.load_scene(art.files["glb"])
    turn = trimesh.geometry.align_vectors([0.0, 1.0, 0.0], CAMERA)
    scene.apply_transform(turn)
    plan = rig.out / f"{name}_plan.glb"
    scene.export(plan)
    pngs = [rig.geometry.thumbnail(glb, rig.out / f"{name}_{view}.png", 512) for view, glb in (("iso", art.files["glb"]), ("plan", plan))]
    return [p.read_bytes() for p in pngs]


ROWS: dict[str, Demo] = {"IN-4": in_4, "IN-5": in_5, "IN-6": in_6, "VM-10": vm_10}
