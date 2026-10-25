import hashlib
from typing import Any

from partwright_ir.model import Design


def json_schema() -> dict[str, Any]:
    return Design.model_json_schema()


def design_hash(design: Design) -> str:
    return hashlib.sha256(design.model_dump_json().encode()).hexdigest()[:16]
