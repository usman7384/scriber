from typing import Any

from partwright_ir.model import Design, Param
from partwright_ir.validate import NON_EXPR_FIELDS, used_params

COUNT_FIELDS = {"count", "count_x", "count_y"}
ANGLE_FIELDS = {"angle", "start_angle"}


def normalize(design: Design) -> Design:
    unused = [p for p in design.params if p.name not in used_params(design)]
    if not unused:
        return design
    data = design.model_dump(mode="json")
    for part in data["parts"]:
        for node in [*part["sketches"], *part["features"]]:
            _substitute(node, unused, None)
    return Design.model_validate(data)


def _substitute(node: Any, unused: list[Param], field: str | None) -> Any:
    if isinstance(node, dict):
        for key, value in node.items():
            if key not in NON_EXPR_FIELDS and key != "provenance":
                node[key] = _substitute(value, unused, key)
        return node
    if isinstance(node, list):
        return [_substitute(v, unused, field) for v in node]
    if isinstance(node, int | float) and not isinstance(node, bool) and node != 0:
        match = next((p.name for p in unused if p.value == node and p.unit == _unit(field)), None)
        return match or node
    return node


def _unit(field: str | None) -> str:
    if field in COUNT_FIELDS:
        return ""
    if field in ANGLE_FIELDS:
        return "deg"
    return "mm"


def drop_unused_params(design: Design) -> Design:
    used = used_params(design)
    return design.model_copy(update={"params": [p for p in design.params if p.name in used]})
