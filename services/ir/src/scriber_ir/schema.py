import hashlib
import json
from typing import Any

from pydantic import BaseModel

from scriber_ir.model import Design


def json_schema() -> dict[str, Any]:
    return Design.model_json_schema()


def design_hash(design: Design) -> str:
    # a design keeps the hash it had before later fields existed, as long as it leaves them at their defaults
    exclude: dict[str, Any] = {"parts": {i: {"face_groups"} for i, p in enumerate(design.parts) if not p.face_groups}}
    if design.assembly is None:
        exclude["assembly"] = True
    data = _without_new_defaults(json.loads(design.model_dump_json(exclude=exclude)))
    return hashlib.sha256(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:16]


# fields added after designs were saved, with the value that means "not used"
NEW_DEFAULTS: dict[str, Any] = {
    "meets": None,
    "origin": None,
    "normal": None,
    "x_dir": None,
    "wall": None,
    "instances": [],
    "reference": False,
    "geom": "any",
    "arc_radius": None,
    "outline": False,
    "through": "all",
    "center": None,
    "thread_depth": None,
    "modelled": False,
    "relief": None,
    "flanges": [],
    "wrap": None,
    "fit": None,
    "tol_plus": None,
    "tol_minus": None,
}

# fields added to one kind only, whose name other kinds already use with a different default
KIND_DEFAULTS: dict[Any, dict[str, Any]] = {"loft": {"mode": "add"}, "rect": {"angle": 0.0}}


def _without_new_defaults(node: Any) -> Any:
    if isinstance(node, list):
        return [_without_new_defaults(n) for n in node]
    if not isinstance(node, dict):
        return node
    added = {**NEW_DEFAULTS, **KIND_DEFAULTS.get(node.get("kind"), {})}
    kept = {k: v for k, v in node.items() if not (k in added and v == added[k])}
    return {k: _without_new_defaults(v) for k, v in kept.items()}


def answer_json(model: BaseModel) -> str:
    # schema-constrained decoding emits required keys before optional ones; answers we show or train on must use that order
    return json.dumps(_ordered(model), separators=(",", ":"))


def _ordered(value: Any) -> Any:
    if isinstance(value, BaseModel):
        fields = type(value).model_fields
        names = [n for n, f in fields.items() if f.is_required()] + [n for n, f in fields.items() if not f.is_required()]
        return {
            n: _ordered(getattr(value, n))
            for n in names
            if fields[n].is_required() or getattr(value, n) != fields[n].get_default(call_default_factory=True)
        }
    if isinstance(value, list | tuple):
        return [_ordered(v) for v in value]
    return value
