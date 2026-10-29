import hashlib

from partwright_ir.model import Assembly, Design, Joint, Param, Part
from partwright_ir.normalize import drop_unused_params


class ComponentError(ValueError):
    pass


def part(design: Design, part_id: str) -> Part:
    found = [p for p in design.parts if p.id == part_id]
    if not found:
        raise ComponentError(f"no part {part_id!r}; parts: {[p.id for p in design.parts]}")
    return found[0]


def scope(design: Design, part_id: str) -> Design:
    return drop_unused_params(design.model_copy(update={"parts": [part(design, part_id)], "assembly": None}))


def part_hash(design: Design, part_id: str) -> str:
    scoped = scope(design, part_id)
    text = scoped.parts[0].model_dump_json() + "".join(p.model_dump_json() for p in scoped.params)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def splice(design: Design, edited: Design, part_id: str) -> Design:
    part(design, part_id)
    new = next((p for p in edited.parts if p.id == part_id), edited.parts[0]).model_copy(update={"id": part_id})
    parts = [new if p.id == part_id else p for p in design.parts]
    return design.model_copy(update={"parts": parts, "params": _merge(design.params, edited.params)})


def insert(design: Design, new: Design, mate: str) -> Design:
    if len(new.parts) != 1:
        raise ComponentError(f"the new component must be one part, got {len(new.parts)}")
    (added,) = new.parts
    if added.id in {p.id for p in design.parts}:
        raise ComponentError(f"part id {added.id!r} is already used in the assembly; choose another")
    host = design.assembly or Assembly()
    if mate not in {c.id for c in host.connectors}:
        raise ComponentError(f"the assembly has no connector {mate!r}")
    own = [c for c in (new.assembly.connectors if new.assembly else []) if c.part == added.id]
    if len(own) != 1:
        raise ComponentError(f"give part {added.id!r} exactly one connector where it seats on {mate!r}, got {len(own)}")
    clash = {c.id for c in own} & {c.id for c in host.connectors}
    if clash:
        raise ComponentError(f"connector ids {sorted(clash)} are already used in the assembly")
    joint = Joint(id=f"{added.id}_on_{mate}", parent=mate, child=own[0].id)
    assembly = Assembly(connectors=[*host.connectors, *own], joints=[*host.joints, joint])
    params = _merge(design.params, new.params, strict=True)
    return design.model_copy(update={"parts": [*design.parts, added], "params": params, "assembly": assembly})


def _merge(base: list[Param], extra: list[Param], strict: bool = False) -> list[Param]:
    known = {p.name: p for p in base}
    clash = [p.name for p in extra if p.name in known and known[p.name].value != p.value]
    if strict and clash:
        raise ComponentError(f"parameters {clash} already have other values in the assembly; rename them in the new part")
    updated = {} if strict else {p.name: p for p in extra}
    return [updated.get(p.name, p) for p in base] + [p for p in extra if p.name not in known]
