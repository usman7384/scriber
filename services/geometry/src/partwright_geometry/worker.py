import builtins
import json
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

from build123d import Compound, Shape, export_gltf, export_step, export_stl

from partwright_geometry.dfm import dfm_findings
from partwright_geometry.imports import describe, step_parts
from partwright_geometry.joints import interferences, mate_checks
from partwright_geometry.metrics import part_metrics
from partwright_geometry.sections import span_sections
from partwright_geometry.step_meta import read_step, write_step
from partwright_geometry.structure import part_structure
from partwright_geometry.thumbnail import render_thumbnail
from partwright_ir import RuleSet

ALLOWED_IMPORTS = {"math", "build123d"}
BLOCKED_BUILTINS = {"open", "eval", "exec", "compile", "input", "breakpoint", "__import__"}


def main() -> None:
    for line in sys.stdin:
        print(json.dumps(handle(json.loads(line))), flush=True)


def handle(request: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"ok": True, **OPS[request["op"]](request)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "lines": _user_lines(e)}


def build(request: dict[str, Any]) -> dict[str, Any]:
    rules = RuleSet.model_validate(request["rules"])
    return run(request["source"], Path(request["out_dir"]), request["title"], rules, request.get("materials", {}))


def run(source: str, out_dir: Path, title: str, rules: RuleSet, materials: dict[str, str | None]) -> dict[str, Any]:
    parts, namespace = solids(source)
    mates = namespace.get("MATES")
    model = Compound(label=title, children=list(parts.values()))
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {"step": out_dir / "model.step", "stl": out_dir / "model.stl", "glb": out_dir / "model.glb"}
    faces = namespace.get("FACES", {})
    if faces or any(materials.values()):
        write_step(parts, title, faces, materials, files["step"])
    else:
        export_step(model, files["step"])
    export_stl(model, files["stl"])
    export_gltf(model, str(files["glb"]), binary=True)
    metrics = {pid: part_metrics(pid, s) for pid, s in parts.items()}
    reply: dict[str, Any] = {
        "files": {k: str(v) for k, v in files.items()},
        "parts": [m.model_dump() for m in metrics.values()],
        "findings": [f.model_dump() for pid, s in parts.items() for f in dfm_findings(s, metrics[pid], rules)],
    }
    if mates is not None:
        checks, overlaps = mate_checks(parts, mates, namespace.get("SLACK", {})), interferences(parts)
        reply["assembly"] = {"mates": [m.model_dump() for m in checks], "interferences": [i.model_dump() for i in overlaps]}
    return reply


def solids(source: str) -> tuple[dict[str, Shape[Any]], dict[str, Any]]:
    namespace = _load(source)
    parts: dict[str, Shape[Any]] = namespace["build"]()
    for pid, shape in parts.items():
        if not isinstance(shape, Shape):
            raise TypeError(f"part {pid!r} produced {type(shape).__name__}, not a solid")
    return parts, namespace


def sketch_frames(source: str) -> list[dict[str, Any]]:
    namespace = _load(source)
    ref, extrude, seen = namespace["_ref"], namespace["_extrude"], []

    def recording(part: Any, features: Any, datums: Any, name: str, offset: float) -> Any:
        pl, out = ref(part, features, datums, name, offset)
        seen.append({"ref": name, "origin": _vec(pl.origin), "x_dir": _vec(pl.x_dir), "z_dir": _vec(pl.z_dir), "out": out})
        return pl, out

    def facing(part: Any, sk: Any, pl: Any, *rest: Any) -> Any:
        # build123d extrudes along the face normal, which a clockwise outline turns against the plane normal
        signs = {f.normal_at().dot(pl.z_dir) > 0 for f in sk.faces()}
        seen[-1]["normal"] = 1 if signs == {True} else -1 if signs == {False} else 0
        return extrude(part, sk, pl, *rest)

    # model functions look these up in their globals at call time, so the swap sees every sketch in feature order
    namespace["_ref"], namespace["_extrude"] = recording, facing
    namespace["build"]()
    return seen


def structure(source: str) -> dict[str, Any]:
    namespace = _load(source)
    seen: dict[str, list[tuple[str, Shape[Any]]]] = {}
    namespace["_trace"] = lambda pid, fid, part: seen.setdefault(pid, []).append((fid, part))
    parts: dict[str, Shape[Any]] = namespace["build"]()
    return {pid: part_structure(seen[pid], shape) for pid, shape in parts.items() if pid in seen}


def _load(source: str) -> dict[str, Any]:
    namespace: dict[str, Any] = {"__builtins__": _sandbox_builtins(), "__name__": "partwright_model"}
    exec(compile(source, "model.py", "exec"), namespace)
    return namespace


def _vec(v: Any) -> tuple[float, float, float]:
    return (float(v.X), float(v.Y), float(v.Z))


OPS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "build": build,
    "measure": lambda r: {"parts": [part_metrics(pid, s).model_dump() for pid, s in solids(r["source"])[0].items()]},
    "describe": lambda r: {"descriptor": describe(Path(r["path"])).model_dump()},
    "import_step": lambda r: {"parts": [p.model_dump() for p in step_parts(Path(r["path"]))]},
    "step_metadata": lambda r: {"metadata": read_step(Path(r["path"])).model_dump()},
    "frames": lambda r: {"frames": sketch_frames(r["source"])},
    "structure": lambda r: {"parts": structure(r["source"])},
    "sections": lambda r: {"sections": span_sections(Path(r["path"]), r["ys"])},
    "thumbnail": lambda r: {"png": str(render_thumbnail(Path(r["path"]), Path(r["png"]), r["size"]))},
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
