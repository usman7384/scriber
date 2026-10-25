from collections.abc import Mapping

from partwright_ir.model import Design, Param, Provenance


class ParamError(ValueError):
    pass


def apply_params(design: Design, updates: Mapping[str, float], source: Provenance | None = None) -> Design:
    known = {p.name for p in design.params}
    unknown = set(updates) - known
    if unknown:
        raise ParamError(f"unknown parameters {sorted(unknown)}; known: {sorted(known)}")
    edited = source or Provenance(source="user_edit")
    return design.model_copy(update={"params": [_update(p, updates, edited) for p in design.params]})


def _update(p: Param, updates: Mapping[str, float], source: Provenance) -> Param:
    if p.name not in updates:
        return p
    value = float(updates[p.name])
    if (p.min is not None and value < p.min) or (p.max is not None and value > p.max):
        raise ParamError(f"{p.name}={value:g} outside [{p.min}, {p.max}]")
    return p.model_copy(update={"value": value, "provenance": source})


def label(name: str) -> str:
    return name.replace("_", " ").title()
