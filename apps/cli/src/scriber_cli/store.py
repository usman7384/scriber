import json
import re
import shutil
from pathlib import Path

from scriber_agent import Result, Step, dump_steps
from scriber_ir import Design, label

OK_MARKER = "OK"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "model"


def next_version(model_dir: Path) -> Path:
    return model_dir / f"v{len(versions(model_dir)) + 1}"


def versions(model_dir: Path) -> list[Path]:
    return sorted((p for p in model_dir.glob("v*") if p.is_dir() and p.name[1:].isdigit()), key=lambda p: int(p.name[1:]))


def latest_design(model_dir: Path) -> Design:
    for v in reversed(versions(model_dir)):
        if (v / OK_MARKER).exists():
            return Design.model_validate_json((v / "design.json").read_text(encoding="utf-8"))
    raise FileNotFoundError(f"no successful version in {model_dir}")


def save(version_dir: Path, steps: list[Step], result: Result | None) -> None:
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "steps.json").write_text(dump_steps(steps), encoding="utf-8")
    if result is None or result.artifact is None or result.design is None:
        return
    for path in result.artifact.files.values():
        if path.parent != version_dir:
            shutil.copy2(path, version_dir / path.name)
    (version_dir / "params.json").write_text(json.dumps(params_table(result.design), indent=2), encoding="utf-8")
    (version_dir / "result.json").write_text(result.model_dump_json(indent=2, exclude={"design"}), encoding="utf-8")
    if result.ok:
        (version_dir / OK_MARKER).touch()


def params_table(design: Design) -> list[dict[str, object]]:
    return [{"label": label(p.name), **p.model_dump(mode="json")} for p in design.params]
