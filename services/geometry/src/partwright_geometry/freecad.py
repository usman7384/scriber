import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from partwright_geometry.models import Frozen

SCRIPTS = Path(__file__).parent
TIMEOUT_S = 600
# FreeCAD ships its own Python; our interpreter's variables must not leak into it
PYTHON_VARS = ("PYTHONPATH", "PYTHONHOME", "PYTHONSAFEPATH", "VIRTUAL_ENV")


class FreeCadError(RuntimeError):
    pass


class FreeCadStep(Frozen):
    solids: int
    valid: bool
    volume: float
    exported: Path


class FcstdFeature(Frozen):
    name: str
    label: str
    type: str
    valid: bool
    dof: int | None = None
    constraints: int | None = None
    conflicting: int | None = None
    redundant: int | None = None
    expressions: int = 0


class FcstdBody(Frozen):
    name: str
    label: str
    features: list[FcstdFeature]
    solids: int
    valid: bool
    volume: float


class FcstdReport(Frozen):
    bodies: list[FcstdBody]
    errors: list[str]
    edited: dict[str, Path]


def alias(param: str) -> str:
    # spreadsheet aliases may not be unit symbols or constants (t, h, mm, in, e, ...); none contains "_" or is that long
    return param if "_" in param or len(param) > 4 else f"{param}_"


def run_freecad(freecad: Path, script: str, args: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="partwright-freecad-") as tmp:
        args_file, result = Path(tmp) / "args.json", Path(tmp) / "result.json"
        args_file.write_text(json.dumps(args | {"result": str(result)}), encoding="utf-8")
        load = f"ARGS = json.load(open({str(args_file)!r}, encoding='utf-8'))"
        code = f"import json\n{load}\nexec(open({str(SCRIPTS / script)!r}, encoding='utf-8').read())"
        env = {k: v for k, v in os.environ.items() if k not in PYTHON_VARS}
        run = subprocess.run(
            [str(freecad), "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=TIMEOUT_S
        )
        # the answer comes back in a file: freecadcmd interleaves its progress output with anything printed
        if run.returncode != 0 or not result.exists():
            tail = "\n".join((run.stdout + run.stderr).splitlines()[-15:])
            raise FreeCadError(f"FreeCAD {script} failed (exit {run.returncode}):\n{tail}")
        found: dict[str, Any] = json.loads(result.read_text(encoding="utf-8"))
    return found


def step_in_freecad(freecad: Path, step: Path, exported: Path) -> FreeCadStep:
    found = run_freecad(freecad, "freecad_step.FCMacro", {"step": str(step), "out": str(exported)})
    return FreeCadStep.model_validate(found | {"exported": exported})


def inspect_fcstd(freecad: Path, fcstd: Path, edits: dict[str, float], step_dir: Path) -> FcstdReport:
    step_dir.mkdir(parents=True, exist_ok=True)
    changes = [{"name": k, "alias": alias(k), "value": v} for k, v in edits.items()]
    args = {"path": str(fcstd), "edits": changes, "step_dir": str(step_dir)}
    return FcstdReport.model_validate(run_freecad(freecad, "fcstd_inspect.FCMacro", args))
