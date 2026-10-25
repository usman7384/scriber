from pydantic import BaseModel, ConfigDict

from partwright_agent.requirements import Requirement
from partwright_agent.standards import ISO273_RANGE
from partwright_context import ContextPack, Fact
from partwright_ir import Design, Param, Process, RuleSet

MAX_FACTS = 24


class Grounding(BaseModel):
    model_config = ConfigDict(frozen=True)
    pack: ContextPack
    rules: RuleSet
    process: Process = "any"

    def used_ids(self) -> list[str]:
        ids = [c.doc_id for c in self.pack.chunks] + [f.id for f in [*self.pack.facts, *self.pack.conventions]]
        return list(dict.fromkeys([*ids, *(r.id for r in self.rules.rules)]))


def context_block(g: Grounding) -> str:
    facts = [*g.pack.conventions, *(f for f in g.pack.facts if f not in g.pack.conventions)][:MAX_FACTS]
    lines = [
        "Project data. When a parameter comes from one of these facts, set its provenance to "
        '{"source": "document", "ref": "<fact id>", "quote": "<the fact text>"}.'
    ]
    lines += [f"- [{f.id}] {_describe(f)}: {f.text}" for f in facts if f.kind != "material" or f in g.pack.conventions]
    if g.pack.conventions:
        lines.append("Team conventions: apply them even when the request does not mention them.")
    if g.rules.rules:
        lines.append("Design rules the part must satisfy:")
        lines += [f"- [{r.id}] {r.text or r.kind}" for r in g.rules.rules]
    prior = _prior(g.pack)
    if prior:
        lines.append(prior)
    return "\n".join(lines)


def fact_requirements(facts: list[Fact]) -> list[Requirement]:
    out: dict[tuple[object, ...], Requirement] = {}
    for f in facts:
        r = _requirement(f)
        if r is not None:
            out.setdefault((r.kind, r.value, r.count, r.diameter_min, r.diameter_max), r)
    return list(out.values())


def cite(design: Design, pack: ContextPack) -> Design:
    by_id = {f.id: f for f in [*pack.facts, *pack.conventions]}
    return design.model_copy(update={"params": [_cited(p, by_id) for p in design.params]})


def _cited(p: Param, facts: dict[str, Fact]) -> Param:
    fact = facts.get(p.provenance.ref or "")
    return p.model_copy(update={"provenance": fact.source}) if fact else p


def _requirement(f: Fact) -> Requirement | None:
    label = f"{f.text} [{f.id}]"
    if f.kind == "holes" and isinstance(f.value, float):
        lo, hi = ISO273_RANGE.get(f.name.upper(), (f.value - 0.1, f.value + 0.1))
        return Requirement(kind="holes", description=label, count=f.count, diameter_min=lo, diameter_max=hi)
    if f.kind == "tolerance" and isinstance(f.value, float) and f.tol and f.unit == "mm":
        lo, hi = f.value + f.tol[0], f.value + f.tol[1]
        if f.name == "diameter" and any(w in f.text.lower() for w in ("bore", "hole")):
            return Requirement(kind="holes", description=label, diameter_min=lo, diameter_max=hi)
        return Requirement(kind="extent", description=label, value=f.value, tolerance=max(abs(f.tol[0]), f.tol[1]))
    if f.kind == "parameter" and f.name.endswith(("size_x", "size_y", "size_z")) and isinstance(f.value, float):
        return Requirement(kind="extent", description=label, value=f.value)
    return None


def _describe(f: Fact) -> str:
    tol = f" ({f.tol[0]:+g}/{f.tol[1]:+g})" if f.tol else ""
    count = f"{f.count} x " if f.count else ""
    return f"{f.name} = {count}{f.value}{f.unit}{tol}"


def _prior(pack: ContextPack) -> str | None:
    best = next((p for p in pack.similar_parts if p.design is not None), None)
    if best is not None and best.design is not None:
        return "A similar part designed earlier in this project; reuse its structure where it fits:\n" + best.design.model_dump_json(
            exclude_defaults=True
        )
    shape = next((p for p in pack.similar_parts if p.descriptor is not None), None)
    if shape is not None and shape.descriptor is not None:
        d = shape.descriptor
        size = " x ".join(f"{v:g}" for v in d.bbox_sorted)
        holes = ", ".join(f"{h:g}" for h in d.hole_diameters) or "none"
        return f"A similar uploaded part {shape.name}: overall {size} mm, hole diameters {holes} mm."
    return None
