import re
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from scriber_agent.requirements import CheckResult, Requirement
from scriber_agent.standards import ISO273_RANGE
from scriber_context import ContextPack, Fact
from scriber_ir import Design, Param, Process, RuleSet, answer_json

MAX_FACTS = 24
HELD = re.compile(r"insert|heat-?set|tapped|thread", re.IGNORECASE)


class Grounding(BaseModel):
    model_config = ConfigDict(frozen=True)
    pack: ContextPack
    rules: RuleSet
    process: Process = "any"

    def used_ids(self) -> list[str]:
        ids = [c.doc_id for c in self.pack.chunks] + [f.id for f in [*self.pack.facts, *self.pack.conventions]]
        return list(dict.fromkeys([*ids, *(r.id for r in self.rules.rules)]))


def context_block(g: Grounding, overridden: Sequence[Fact] = ()) -> str:
    rule_lines = {r.source.ref for r in g.rules.rules if r.source.ref}
    candidates = [*g.pack.conventions, *(f for f in g.pack.facts if f not in g.pack.conventions)]
    facts = [f for f in candidates if f.source.ref not in rule_lines and f not in overridden][:MAX_FACTS]
    lines = [
        "Project data. When a parameter comes from one of these facts, set its provenance to "
        '{"source": "document", "ref": "<fact id>", "quote": "<the fact text>"}. '
        "Where the request states a different value, the request wins."
    ]
    lines += [f"- [{f.id}] {_describe(f)}: {f.text}" for f in facts if f.kind != "material" or f in g.pack.conventions]
    if g.pack.conventions:
        lines.append("Team conventions: apply them even when the request does not mention them.")
    if g.rules.rules:
        lines.append("Design rules the part must satisfy. They are checked automatically, so do not add parameters for them:")
        lines += [f"- [{r.id}] {r.text or r.kind}" for r in g.rules.rules]
    prior = _prior(g.pack)
    if prior:
        lines.append(prior)
    return "\n".join(lines)


def overridden(stated: list[Requirement], facts: list[Fact]) -> list[Fact]:
    return [f for f in facts if (r := _requirement(f)) is not None and _conflicts(r, stated)]


def _conflicts(r: Requirement, stated: list[Requirement]) -> bool:
    same = [s for s in stated if s.kind == r.kind]
    if r.kind == "extent" and r.value is not None:
        values = [s for s in same if s.value is not None]
        return bool(values) and not any(abs(s.value - r.value) <= max(s.tolerance, r.tolerance) for s in values if s.value is not None)
    if r.kind == "holes" and r.count is not None:
        counted = [s for s in same if s.count is not None]
        return bool(counted) and not any(s.count == r.count and _overlap(s, r) for s in counted)
    return False


def _overlap(a: Requirement, b: Requirement) -> bool:
    lo = max(a.diameter_min or 0.0, b.diameter_min or 0.0)
    return lo <= min(a.diameter_max or float("inf"), b.diameter_max or float("inf"))


def fact_requirements(facts: list[Fact]) -> list[Requirement]:
    out: dict[tuple[object, ...], Requirement] = {}
    for f in facts:
        r = _requirement(f)
        if r is not None:
            out.setdefault(_key(r), r)
    return list(out.values())


def coverage(facts: Sequence[Fact], checks: Sequence[CheckResult]) -> list[tuple[Fact, CheckResult | None]]:
    by_key = {_key(c.requirement): c for c in checks}
    return [(f, by_key.get(_key(r)) if (r := _requirement(f)) else None) for f in facts if isinstance(f.value, float)]


def _key(r: Requirement) -> tuple[object, ...]:
    return (r.kind, r.value, r.tolerance, r.count, r.diameter_min, r.diameter_max)


def cite(design: Design, pack: ContextPack) -> Design:
    by_id = {f.id: f for f in [*pack.facts, *pack.conventions]}
    return design.model_copy(update={"params": [_cited(p, by_id) for p in design.params]})


def _cited(p: Param, facts: dict[str, Fact]) -> Param:
    fact = facts.get(p.provenance.ref or "")
    return p.model_copy(update={"provenance": fact.source}) if fact else p


def _requirement(f: Fact) -> Requirement | None:
    label = f"{f.text} [{f.id}]"
    if f.kind == "holes" and isinstance(f.value, float):
        thread = f"M{f.value:g}"
        is_thread = re.search(rf"\b{re.escape(thread)}\b", f.text) is not None
        lo, hi = ISO273_RANGE[thread] if is_thread and thread in ISO273_RANGE else (f.value - 0.1, f.value + 0.1)
        if is_thread and HELD.search(f.text):
            # tapped or insert holes: from the tap drill (about 0.8 d) to a heat-set insert bore (about 1.4 d)
            lo, hi = 0.75 * f.value, 1.45 * f.value
        return Requirement(kind="holes", description=label, count=f.count, diameter_min=lo, diameter_max=hi)
    if f.kind == "tolerance" and isinstance(f.value, float) and f.tol and f.unit == "mm":
        lo, hi = f.value + f.tol[0], f.value + f.tol[1]
        is_diameter = "diameter" in f.name or any(c in f.text for c in "Ø⌀")
        if is_diameter and any(w in f.text.lower() for w in ("bore", "hole")):
            return Requirement(kind="holes", description=label, diameter_min=lo, diameter_max=hi)
        return Requirement(kind="extent", description=label, value=f.value, tolerance=max(abs(f.tol[0]), f.tol[1]))
    if f.kind == "parameter" and f.name.endswith(("size_x", "size_y", "size_z")) and isinstance(f.value, float):
        return Requirement(kind="extent", description=label, value=f.value)
    return None


def _describe(f: Fact) -> str:
    tol = f" ({f.tol[0]:+g}/{f.tol[1]:+g})" if f.tol else ""
    count = f"{f.count} x " if f.count else ""
    at = f" at x={f.at[0]:g}, y={f.at[1]:g}" if f.at else ""
    return f"{f.name} = {count}{f.value}{f.unit}{tol}{at}"


def _prior(pack: ContextPack) -> str | None:
    best = next((p for p in pack.similar_parts if p.design is not None), None)
    if best is not None and best.design is not None:
        return "A similar part designed earlier in this project; reuse its structure where it fits:\n" + answer_json(best.design)
    shape = next((p for p in pack.similar_parts if p.descriptor is not None), None)
    if shape is not None and shape.descriptor is not None:
        d = shape.descriptor
        size = " x ".join(f"{v:g}" for v in d.bbox_sorted)
        holes = ", ".join(f"{h:g}" for h in d.hole_diameters) or "none"
        return f"A similar uploaded part {shape.name}: overall {size} mm, hole diameters {holes} mm."
    return None
