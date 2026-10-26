import random

from partwright_agent import Grounding
from partwright_context import DEFAULT_RULES, ContextPack, Fact, PartRef
from partwright_ir import Provenance, RuleSet
from partwright_training.spec import Spec, num

RULES: RuleSet = DEFAULT_RULES.for_process("any")
OTHER_SIZES = ("M4", "M5", "M6", "M8", "M10")


def grounding(spec: Spec, rng: random.Random, prior: Spec | None) -> Grounding | None:
    if rng.random() < 0.4:
        return None
    facts = _conflicting(spec, rng) if rng.random() < 0.3 else []
    similar = (
        [PartRef(id="prior", name=prior.title, origin="generated", design=prior.design, score=0.8)] if prior and rng.random() < 0.2 else []
    )
    pack = ContextPack(query=spec.title, chunks=[], facts=facts, rules=list(RULES.rules), similar_parts=similar, conventions=[])
    return Grounding(pack=pack, rules=RULES)


def _conflicting(spec: Spec, rng: random.Random) -> list[Fact]:
    doc = f"d{rng.getrandbits(48):012x}"
    sizes = [round(c.value * rng.choice((0.7, 0.8, 1.2, 1.25)), 0) for c in spec.checks if c.kind == "extent" and c.value][:3]
    facts = [
        _fact(doc, i, "parameter", f"part_size_{axis}", v, f"REQ-1 Part size {' x '.join(num(s) for s in sizes)} mm")
        for i, (axis, v) in enumerate(zip("xyz", sizes, strict=False))
    ]
    counted = [c for c in spec.checks if c.kind == "holes" and c.count and c.count > 1]
    if counted:
        size = rng.choice(OTHER_SIZES)
        text = f"REQ-2 Mounting: {counted[0].count} x {size} through holes"
        facts.append(_fact(doc, 9, "holes", "req_2_mounting", float(size[1:]), text, count=counted[0].count))
    return facts


def _fact(doc: str, i: int, kind: str, name: str, value: float, text: str, count: int | None = None) -> Fact:
    source = Provenance(source="document", ref=f"{doc}#p1:l{i + 2}", quote=text)
    return Fact(
        id=f"{doc}:1.{i + 2}.0",
        doc_id=doc,
        kind=kind,
        name=name,
        value=value,
        unit="mm",
        count=count,
        page=1,
        line=i + 2,
        text=text,
        source=source,
    )
