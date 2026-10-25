import builtins
import json
import sys
import traceback
from pathlib import Path
from typing import Any

from build123d import Compound, Shape, export_gltf, export_step, export_stl

from partwright_geometry.metrics import part_metrics

ALLOWED_IMPORTS = {"math", "build123d"}
BLOCKED_BUILTINS = {"open", "eval", "exec", "compile", "input", "breakpoint", "__import__"}


def main() -> None:
    for line in sys.stdin:
        print(json.dumps(handle(json.loads(line))), flush=True)


def handle(request: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"ok": True, **run(request["source"], Path(request["out_dir"]), request["title"])}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "lines": _user_lines(e)}


def run(source: str, out_dir: Path, title: str) -> dict[str, Any]:
    namespace: dict[str, Any] = {"__builtins__": _sandbox_builtins(), "__name__": "partwright_model"}
    exec(compile(source, "model.py", "exec"), namespace)
    parts: dict[str, Shape[Any]] = namespace["build"]()
    for pid, shape in parts.items():
        if not isinstance(shape, Shape):
            raise TypeError(f"part {pid!r} produced {type(shape).__name__}, not a solid")
    model = Compound(label=title, children=list(parts.values()))
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {"step": out_dir / "model.step", "stl": out_dir / "model.stl", "glb": out_dir / "model.glb"}
    export_step(model, files["step"])
    export_stl(model, files["stl"])
    export_gltf(model, str(files["glb"]), binary=True)
    return {
        "files": {k: str(v) for k, v in files.items()},
        "parts": [part_metrics(pid, s).model_dump() for pid, s in parts.items()],
    }


def _sandbox_builtins() -> dict[str, Any]:
    safe = {k: v for k, v in vars(builtins).items() if k not in BLOCKED_BUILTINS}

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.split(".")[0] not in ALLOWED_IMPORTS:
            raise ImportError(f"import of {name!r} is not allowed in model code")
        return builtins.__import__(name, *args, **kwargs)

    safe["__import__"] = guarded_import
    return safe


def _user_lines(e: Exception) -> list[int]:
    return [f.lineno or 0 for f in traceback.extract_tb(e.__traceback__) if f.filename == "model.py"]


if __name__ == "__main__":
    main()
