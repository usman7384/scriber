import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException

from partwright_api import disk
from partwright_api.deps import Deps
from partwright_api.schemas import Tools
from partwright_geometry import BuildError, FreeCadError, SliceReport, UnsupportedExportError, export_fcstd, slice_stl

TOOL_ERRORS = (FreeCadError, BuildError, OSError, subprocess.TimeoutExpired)


def available(d: Deps) -> Tools:
    return Tools(freecad=d.settings.freecad is not None, prusaslicer=d.settings.prusaslicer is not None)


def need_tool(path: Path | None, name: str, variable: str) -> Path:
    if path is None:
        raise HTTPException(503, f"{name} is not configured: set {variable} to its executable")
    return path


def fcstd(d: Deps, freecad: Path, version: Path) -> bytes:
    design = disk.design(version)
    with tempfile.TemporaryDirectory(prefix="partwright-fcstd-") as tmp:
        try:
            return export_fcstd(design, d.geometry.frames(design), freecad, Path(tmp) / "model.FCStd").read_bytes()
        except UnsupportedExportError as e:
            raise HTTPException(422, f"this design has no FreeCAD export: {e}") from None
        except TOOL_ERRORS as e:
            raise HTTPException(502, f"FreeCAD export failed: {e}") from None


def slice_version(prusaslicer: Path, stl: Path) -> SliceReport:
    # the G-code is only counted, so it goes with the temporary directory
    with tempfile.TemporaryDirectory(prefix="partwright-gcode-") as tmp:
        try:
            return slice_stl(prusaslicer, stl, Path(tmp) / "model.gcode")
        except TOOL_ERRORS as e:
            raise HTTPException(502, f"PrusaSlicer failed: {e}") from None
