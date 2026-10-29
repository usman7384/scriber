import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

from partwright_context.aircraft import aircraft_design
from partwright_context.sizing import AircraftSpec, SizingAdapter, Sourced, XmlSizing
from partwright_evals.parity import Demo, Evidence, Measured, Rig, evidence
from partwright_geometry import Artifact
from partwright_ir import Design, Provenance, diff
from partwright_ir.airfoil import naca4

FIXTURES = Path(__file__).parents[2] / "parity" / "m4" / "aircraft"
SNAKE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
FEATURE_COMMENT = re.compile(r"^    # (\S+) ", re.MULTILINE)
BWB_TREE = [
    *("root_airfoil", "mid_airfoil", "tip_airfoil", "main_wing"),
    *("winglet_root_airfoil", "winglet_tip_airfoil", "winglet", "winglet_assembly", "full_aircraft"),
]
Array = npt.NDArray[np.float64]


@dataclass(frozen=True)
class SectionFit:
    chord: float
    le_x: float
    le_z: float
    incidence: float
    deviation_pct: float


def fit_section(points: list[tuple[float, float, float]], naca: str, iterations: int = 30) -> SectionFit:
    # best-fit similarity transform (ICP) of the NACA outline onto the cut; deviation is the worst residual in % chord
    measured = np.array([(x, z) for x, _, z in points])
    ref = _outline(naca)
    te = measured[np.argmax(measured[:, 0])]
    le = measured[np.argmax(np.linalg.norm(measured - te, axis=1))]
    scale, d = float(np.linalg.norm(te - le)), (te - le) / np.linalg.norm(te - le)
    rot, shift = np.array([[d[0], -d[1]], [d[1], d[0]]]), le
    for _ in range(iterations):
        matched = ref[_nearest(measured, scale * ref @ rot.T + shift)]
        rot, scale, shift = _procrustes(matched, measured)
    residual = _distances(measured, scale * ref @ rot.T + shift)
    angle = math.degrees(math.atan2(rot[1, 0], rot[0, 0]))
    return SectionFit(scale, float(shift[0]), float(shift[1]), -angle, float(residual.max()) / scale * 100)


def _outline(naca: str) -> Array:
    points = np.array(naca4(naca, 1000))
    trailing_edge = points[-1] + (points[0] - points[-1]) * np.linspace(0, 1, 20)[:, None]
    return np.vstack([points, trailing_edge])


def _nearest(points: Array, curve: Array) -> npt.NDArray[np.intp]:
    return np.argmin(((points[:, None, :] - curve[None, :, :]) ** 2).sum(-1), axis=1)


def _distances(points: Array, curve: Array) -> Array:
    near = _nearest(points, curve)
    return np.minimum(*(_to_segment(points, curve[np.clip(near + k, 0, len(curve) - 1)], curve[near]) for k in (-1, 1)))


def _to_segment(p: Array, a: Array, b: Array) -> Array:
    ab = b - a
    t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab**2).sum(1), 1e-30), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def _procrustes(a: Array, b: Array) -> tuple[Array, float, Array]:
    ca, cb = a - a.mean(0), b - b.mean(0)
    u, s, vt = np.linalg.svd(cb.T @ ca)
    flip = np.diag([1.0, float(np.sign(np.linalg.det(u @ vt)))])
    rot = u @ flip @ vt
    scale = float((s * np.diag(flip)).sum() / (ca**2).sum())
    return rot, scale, b.mean(0) - scale * a.mean(0) @ rot.T


def build(rig: Rig, design: Design, name: str) -> Artifact:
    return rig.geometry.build(design, rig.out / name)


def wing_checks(rig: Rig, spec: AircraftSpec, art: Artifact) -> tuple[Measured, list[bool]]:
    wing, body = spec.wing, spec.body
    half, inner = wing.span.value / 2, body.width.value / 2 if body else 0.0
    root, tip = (fit_section(s, wing.naca) for s in rig.geometry.sections(art.files["step"], [-inner, -half]))
    (part,) = art.parts
    panel = half - inner
    sweep = math.degrees(math.atan2(tip.le_x - root.le_x, panel))
    dihedral = math.degrees(math.atan2(tip.le_z - root.le_z, panel))
    twist = root.incidence - tip.incidence
    deviation = max(root.deviation_pct, tip.deviation_pct)
    m: Measured = {
        "solids": part.solids,
        "valid": part.valid,
        "span": round(part.bbox_size[1], 3),
        "root_chord": round(root.chord, 3),
        "tip_chord": round(tip.chord, 3),
        "sweep_deg": round(sweep, 3),
        "dihedral_deg": round(dihedral, 3),
        "twist_deg": round(twist, 3),
        "airfoil_deviation_pct_chord": round(deviation, 4),
    }
    checks = [
        part.solids == 1,
        part.valid,
        abs(part.bbox_size[1] - wing.span.value) <= 1,
        abs(root.chord - wing.root_chord.value) <= 0.5,
        abs(tip.chord - wing.tip_chord.value) <= 0.5,
        abs(sweep - wing.sweep.value) <= 0.2,
        abs(dihedral - wing.dihedral.value) <= 0.2,
        abs(twist - wing.twist.value) <= 0.2,
        deviation <= 0.2,
    ]
    return m, checks


def in_11(rig: Rig) -> Evidence:
    spec = XmlSizing().read(FIXTURES / "sizing.xml")
    m, checks = wing_checks(rig, spec, build(rig, aircraft_design(spec), "wing"))
    return evidence("IN-11", m, *checks, note="sections cut at the root and tip stations; sweep and dihedral at the leading edge")


def cd_6(rig: Rig) -> Evidence:
    adapter: SizingAdapter = XmlSizing()
    xml = rig.out / "sizing.xml"
    shutil.copyfile(FIXTURES / "sizing.xml", xml)
    first = aircraft_design(adapter.read(xml))
    old = build(rig, first, "v1")
    xml.write_text(xml.read_text(encoding="utf-8").replace('<span unit="mm">1000</span>', '<span unit="mm">1100</span>'), encoding="utf-8")
    second = aircraft_design(adapter.read(xml))
    new = build(rig, second, "v2")
    change = diff(first, second)
    changed = ", ".join(f"{c.name}: {c.old:g} -> {c.new:g}" for c in change.params if c.old is not None and c.new is not None)
    kept = rig.geometry.import_step(old.files["step"])[0].bbox_size[1]
    span = new.parts[0].bbox_size[1]
    m: Measured = {
        "changed": changed,
        "features_changed": len(change.features_changed),
        "new_span": round(span, 3),
        "old_span": round(kept, 3),
    }
    checks = [changed == "wing_span: 1000 -> 1100", not change.features_changed, abs(span - 1100) <= 1]
    return evidence("CD-6", m, *checks, abs(kept - 1000) <= 1, note="re-run is explicit; no file watcher yet")


def ge_4(rig: Rig) -> Evidence:
    design = aircraft_design(XmlSizing().read(FIXTURES / "bwb.xml"))
    art = build(rig, design, "bwb")
    names = [f.name for f in design.parts[0].features]
    built = FEATURE_COMMENT.findall(art.files["py"].read_text(encoding="utf-8"))
    m: Measured = {"features": ", ".join(names), "build_order": ", ".join(built), "solids": art.parts[0].solids}
    checks = [
        names == BWB_TREE,
        built == [f.id for f in design.parts[0].features],
        not any("imported" in n for n in names),
        all(SNAKE.match(n) for n in names),
        len(set(names)) == len(names),
        art.parts[0].solids == 1 and art.parts[0].valid,
    ]
    return evidence("GE-4", m, *checks)


def dp_9(rig: Rig) -> Evidence:
    spec = _from_params(XmlSizing().read(FIXTURES / "bwb.xml"))
    design = aircraft_design(spec)
    art = build(rig, design, "bwb")
    m, checks = wing_checks(rig, spec, art)
    names = [f.name for f in design.parts[0].features]
    tree = {"root_airfoil", "mid_airfoil", "tip_airfoil", "main_wing", "winglet_tip_airfoil", "winglet_assembly", "full_aircraft"}
    m = {**m, "bbox_cm": " / ".join(f"{s / 10:.1f}" for s in art.parts[0].bbox_size), "tree": ", ".join(names)}
    return evidence("DP-9", m, *checks, tree <= set(names), note="winglets sit inboard of the tips, so the bbox span is the wing span")


def _from_params(bwb: AircraftSpec) -> AircraftSpec:
    given = {"span": 1000.0, "root_chord": 250.0, "tip_chord": 120.0, "sweep": 20.0, "dihedral": 5.0, "twist": 0.0}
    labels = {"span": "Wing Span", "root_chord": "Root Chord", "tip_chord": "Tip Chord", "sweep": "Sweep", "dihedral": "Dihedral"}
    wing = {
        k: Sourced(value=v, provenance=Provenance(source="prompt", quote=f"{labels[k]} {v:.1f}" if k in labels else None))
        for k, v in given.items()
    }
    return bwb.model_copy(update={"wing": bwb.wing.model_copy(update=wing), "inner_volume_mm3": None})


def dp_10(rig: Rig) -> Evidence:
    spec = XmlSizing().read(FIXTURES / "bwb.xml")
    if not (spec.body and spec.inner_volume_mm3):
        raise ValueError("bwb.xml needs a body and an inner volume requirement")
    art = build(rig, aircraft_design(spec), "bwb")
    m, checks = wing_checks(rig, spec, art)
    (outline,) = rig.geometry.sections(art.files["step"], [0.0])
    body = fit_section(outline, spec.body.naca)
    volume, need = art.parts[0].volume, spec.inner_volume_mm3.value
    extra: Measured = {
        "body_chord": round(body.chord, 3),
        "body_deviation_pct_chord": round(body.deviation_pct, 4),
        "inner_volume_l": round(volume / 1e6, 3),
        "required_l": round(need / 1e6, 3),
    }
    checks += [abs(body.chord - spec.body.chord.value) <= 0.5, body.deviation_pct <= 0.2, volume >= need]
    return evidence("DP-10", {**m, **extra}, *checks, note="control surfaces and performance fields are read but not modelled")


ROWS: dict[str, Demo] = {"IN-11": in_11, "CD-6": cd_6, "GE-4": ge_4, "DP-9": dp_9, "DP-10": dp_10}
