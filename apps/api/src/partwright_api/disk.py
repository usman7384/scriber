import json
import shutil
from pathlib import Path

from partwright_agent import Result, Step, dump_steps
from partwright_ir import Design, label

FILE_NAMES = {"step": "model.step", "stl": "model.stl", "glb": "model.glb", "py": "model.py", "ir": "design.json"}
THUMBNAIL = "thumbnail.png"
OK_MARKER = "OK"
MEDIA_TYPES = {"step": "model/step", "stl": "model/stl", "glb": "model/gltf-binary", "py": "text/x-python", "ir": "application/json"}


def model_dir(data_dir: Path, model_id: str) -> Path:
    return data_dir / "models" / model_id


def version_dir(data_dir: Path, model_id: str, number: int) -> Path:
    return model_dir(data_dir, model_id) / f"v{number}"


def next_number(data_dir: Path, model_id: str) -> int:
    root = model_dir(data_dir, model_id)
    return len([p for p in root.glob("v*") if p.is_dir() and p.name[1:].isdigit()]) + 1


def save(version: Path, steps: list[Step], result: Result | None) -> None:
    version.mkdir(parents=True, exist_ok=True)
    (version / "steps.json").write_text(dump_steps(steps), encoding="utf-8")
    if result is None or result.artifact is None or result.design is None:
        return
    for path in result.artifact.files.values():
        if path.parent != version:
            shutil.copy2(path, version / path.name)
    params = [{"label": label(p.name), **p.model_dump(mode="json")} for p in result.design.params]
    (version / "params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
    (version / "result.json").write_text(result.model_dump_json(indent=2, exclude={"design"}), encoding="utf-8")
    if result.ok:
        (version / OK_MARKER).touch()


def design(version: Path) -> Design:
    return Design.model_validate_json((version / FILE_NAMES["ir"]).read_text(encoding="utf-8"))


def copy_version(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True)
    for path in src.iterdir():
        if path.is_file():
            shutil.copy2(path, dst / path.name)


def upload_path(data_dir: Path, project_id: str, file_id: str, name: str) -> Path:
    return data_dir / "uploads" / project_id / file_id / name
