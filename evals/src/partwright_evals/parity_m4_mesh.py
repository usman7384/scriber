import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh

from partwright_evals.parity import Demo, Evidence, Measured, Rig, evidence
from partwright_geometry import Artifact, HoleInfo, hausdorff, reconstruct_mesh
from partwright_ir import Design, apply_params

FIXTURES = Path(__file__).parents[2] / "parity" / "m4" / "mesh"
SKETCHED = {"extrude", "revolve"}
SCAN_SIGMA = 0.1
SCAN_EDGE = 2.0
SEED = 0


@dataclass(frozen=True)
class RoundTrip:
    design: Design
    artifact: Artifact
    hausdorff_mm: float
    diagonal: float
    seconds: float

    @property
    def deviation_pct(self) -> float:
        return 100 * self.hausdorff_mm / self.diagonal

    @property
    def valid(self) -> bool:
        return self.artifact.ok and [(p.solids, p.valid) for p in self.artifact.parts] == [(1, True)]


@dataclass(frozen=True)
class TrueHole:
    x: float
    y: float
    diameter: float


def round_trip(rig: Rig, stl: Path, name: str) -> RoundTrip:
    start = time.monotonic()
    design = reconstruct_mesh(stl)
    art = rig.geometry.build(design, rig.out / name)
    seconds = time.monotonic() - start
    diag = float(np.linalg.norm(trimesh.load_mesh(stl).extents))
    return RoundTrip(design, art, hausdorff(stl, art.files["stl"]), diag, seconds)


def nominal(rig: Rig, fixture: str) -> tuple[Design, Artifact, Path]:
    design = Design.model_validate_json((FIXTURES / f"{fixture}.json").read_text(encoding="utf-8"))
    art = rig.geometry.build(design, rig.out / f"{fixture}_nominal")
    stl = rig.out / f"{fixture}.stl"
    shutil.copyfile(art.files["stl"], stl)
    return design, art, stl


def scan(src: Path, dst: Path) -> Path:
    mesh = trimesh.load_mesh(src)
    v, f = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, max_edge=SCAN_EDGE)
    noisy = v + np.random.default_rng(SEED).normal(0.0, SCAN_SIGMA, v.shape)
    trimesh.Trimesh(noisy, f, process=False).export(dst)
    return dst


def fit_error(found: list[HoleInfo], truth: list[TrueHole]) -> float:
    vertical = [h for h in found if abs(abs(h.axis[2]) - 1) < 1e-6]
    if not vertical:
        return float("inf")
    worst = 0.0
    for t in truth:
        h = min(vertical, key=lambda h: np.hypot(h.center[0] - t.x, h.center[1] - t.y))
        worst = max(worst, float(np.hypot(h.center[0] - t.x, h.center[1] - t.y)) + abs(h.diameter - t.diameter) / 2)
    return worst


def in_7(rig: Rig) -> Evidence:
    _, _, stl = nominal(rig, "flange")
    rt = round_trip(rig, stl, "rebuilt")
    (rig.out / "reconstructed.json").write_text(rt.design.model_dump_json(indent=2), encoding="utf-8")
    sketched = [f.id for f in rt.design.parts[0].features if f.kind in SKETCHED]
    od = rt.design.param_values().get("outer_diameter")
    edited = rig.geometry.build(apply_params(rt.design, {"outer_diameter": od + 10}), rig.out / "edited") if od else None
    edited_od = max(edited.parts[0].bbox_size[:2]) if edited else None
    edited_ok = bool(edited and edited.ok and [(p.solids, p.valid) for p in edited.parts] == [(1, True)])
    m: Measured = {
        "valid": rt.valid,
        "hausdorff_mm": round(rt.hausdorff_mm, 6),
        "hausdorff_pct_diag": round(rt.deviation_pct, 4),
        "sketch_features": ", ".join(sketched),
        "outer_diameter": od,
        "edited_od": edited_od and round(edited_od, 3),
        "edited_valid": edited_ok,
    }
    od_moved = od is not None and edited_od is not None and abs(edited_od - (od + 10)) <= 0.01
    return evidence("IN-7", m, rt.valid, rt.deviation_pct <= 0.5, len(sketched) >= 3, edited_ok, od_moved)


def pf_5(rig: Rig) -> Evidence:
    _, _, stl = nominal(rig, "flange")
    rt = round_trip(rig, stl, "rebuilt")
    m: Measured = {"seconds": round(rt.seconds, 2), "valid": rt.valid}
    return evidence("PF-5", m, rt.valid, rt.seconds < 300, note="reconstruct + rebuild of the IN-7 flange STL")


def _to_bracket(rig: Rig, prefix: str) -> tuple[Measured, bool]:
    truth = [
        TrueHole(h["center"][0], h["center"][1], h["diameter"])
        for h in json.loads((FIXTURES / "to_bracket.json").read_text(encoding="utf-8"))["holes"]
    ]
    rt = round_trip(rig, FIXTURES / "to_bracket.stl", f"{prefix}_rebuilt")
    err = fit_error(rt.artifact.parts[0].holes, truth)
    m: Measured = {
        f"{prefix}_valid": rt.valid,
        f"{prefix}_hausdorff_mm": round(rt.hausdorff_mm, 4),
        f"{prefix}_hausdorff_pct_diag": round(rt.deviation_pct, 4),
        f"{prefix}_hole_fit_mm": round(err, 4),
    }
    return m, rt.valid and rt.deviation_pct <= 1 and err <= 0.05


def _scanned_mount(rig: Rig) -> tuple[Measured, bool]:
    design, art, stl = nominal(rig, "mount")
    d = design.param_values()["hole_diameter"]
    truth = [TrueHole(h.center[0], h.center[1], h.diameter) for h in art.parts[0].holes if abs(h.diameter - d) < 1e-6]
    noisy = scan(stl, rig.out / "scan.stl")
    rt = round_trip(rig, noisy, "scan_rebuilt")
    err = fit_error(rt.artifact.parts[0].holes, truth)
    diag = float(np.linalg.norm(trimesh.load_mesh(stl).extents))
    to_nominal = 100 * hausdorff(stl, rt.artifact.files["stl"]) / diag
    m: Measured = {
        "scan_valid": rt.valid,
        "scan_hausdorff_mm": round(rt.hausdorff_mm, 4),
        "scan_hausdorff_pct_diag": round(rt.deviation_pct, 4),
        "scan_vs_nominal_pct_diag": round(to_nominal, 4),
        "scan_hole_fit_mm": round(err, 4),
        "scan_holes": len(truth),
    }
    return m, rt.valid and rt.deviation_pct <= 1 and err <= 0.05 and len(truth) == 4


def in_8(rig: Rig) -> Evidence:
    (to, to_ok), (sc, sc_ok) = _to_bracket(rig, "to"), _scanned_mount(rig)
    return evidence("IN-8", {**to, **sc}, to_ok, sc_ok)


def cd_4(rig: Rig) -> Evidence:
    m, ok = _to_bracket(rig, "to")
    note = "reconstruction half only; replacing the part in an assembly with its mates kept needs the M4 assembly IR, not on this branch"
    return evidence("CD-4", {**m, "reconstruction_passed": ok, "assembly": "pending"}, ok, False, note=note)


ROWS: dict[str, Demo] = {"IN-7": in_7, "IN-8": in_8, "CD-4": cd_4, "PF-5": pf_5}
