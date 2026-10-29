import hashlib
import json
from typing import Any

from pydantic import BaseModel

from partwright_ir.model import Design


def json_schema() -> dict[str, Any]:
    return Design.model_json_schema()


def design_hash(design: Design) -> str:
    # a design without an assembly or face groups keeps the hash it had before those existed
    exclude: dict[str, Any] = {"parts": {i: {"face_groups"} for i, p in enumerate(design.parts) if not p.face_groups}}
    if design.assembly is None:
        exclude["assembly"] = True
    return hashlib.sha256(design.model_dump_json(exclude=exclude).encode()).hexdigest()[:16]


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
