# Kernel-side checks for the live web parity run: uv run python apps/web/e2e/live/checks.py stl|wing <file> [sizing.xml]

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import trimesh

from partwright_context.sizing import XmlSizing
from partwright_evals.parity import Rig
from partwright_evals.parity_m4_aircraft import wing_checks
from partwright_evals.tools import PRUSASLICER, missing, tool
from partwright_geometry import Artifact, LocalGeometry, slice_stl


def stl(path: Path) -> dict[str, Any]:
    mesh = trimesh.load_mesh(path)
    report: dict[str, Any] = {
        "triangles": len(mesh.faces),
        "size_mm": [round(float(v), 3) for v in mesh.extents],
        "volume_mm3": round(float(mesh.volume), 1),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
    }
    slicer = tool(PRUSASLICER)
    if slicer is None:
        return {**report, "slicer": missing(PRUSASLICER), "sliced_ok": False}
    sliced = slice_stl(slicer, path, path.with_suffix(".gcode"))
    summary = {k: getattr(sliced, k) for k in ("exit_code", "manifold", "layers", "gcode_bytes", "warnings", "errors")}
    return {**report, "slicer": str(slicer), **summary, "sliced_ok": sliced.ok}


def wing(step: Path, xml: Path) -> dict[str, Any]:
    geometry = LocalGeometry()
    with tempfile.TemporaryDirectory() as out:
        rig = Rig(out=Path(out), geometry=geometry, llm=None, config=None)  # type: ignore[arg-type]
        art = Artifact(design_hash="", files={"step": step}, parts=geometry.import_step(step), findings=[], elapsed_ms=0)
        measured, checks = wing_checks(rig, XmlSizing().read(xml), art)
    return {**measured, "in_11_checks_passed": sum(checks), "in_11_checks": len(checks)}


if __name__ == "__main__":
    kind, *paths = sys.argv[1:]
    print(json.dumps(stl(Path(paths[0])) if kind == "stl" else wing(Path(paths[0]), Path(paths[1]))))
