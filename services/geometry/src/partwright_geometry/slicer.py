import re
import subprocess
import tempfile
from pathlib import Path

from partwright_geometry.models import Frozen

INFO = re.compile(r"^(\w+) = +(.+)$", re.M)
TIMEOUT_S = 600


class SliceReport(Frozen):
    exit_code: int
    manifold: bool
    layers: int
    gcode_bytes: int
    warnings: list[str]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and self.manifold and self.layers > 0 and not self.errors


def slice_stl(prusaslicer: Path, stl: Path, gcode: Path) -> SliceReport:
    # a throwaway datadir keeps the run on PrusaSlicer's built-in defaults and away from the user's profiles
    with tempfile.TemporaryDirectory(prefix="partwright-slicer-") as datadir:
        args = [str(prusaslicer), "--datadir", datadir, "--loglevel", "2", "--info", "--export-gcode", "--output", str(gcode), str(stl)]
        run = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_S, check=False)
    log = (run.stdout + run.stderr).splitlines()
    info = dict(INFO.findall(run.stdout))
    sliced = gcode.read_text(encoding="utf-8", errors="replace") if gcode.exists() else ""
    return SliceReport(
        exit_code=run.returncode,
        manifold=info.get("manifold") == "yes",
        layers=sliced.count(";LAYER_CHANGE"),
        gcode_bytes=gcode.stat().st_size if gcode.exists() else 0,
        warnings=[line for line in log if "warning" in line.lower()],
        errors=[line for line in log if "error" in line.lower()],
    )
