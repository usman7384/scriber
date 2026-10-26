import random
import re

from partwright_agent import Grounding
from partwright_context import DEFAULT_RULES, ContextPack, Fact, PartRef
from partwright_ir import Design, Provenance, RuleSet
from partwright_training.render import Prompt
from partwright_training.spec import Spec, num

RULES: RuleSet = DEFAULT_RULES.for_process("any")
OTHER_SIZES = ("M4", "M5", "M6", "M8", "M10")
DOC_REQUESTS = (
    "{title} per the project requirements",
    "Make the {title} from the attached spec",
    "{title} as specified in the documents",
    "Please model the {title} described in the spec sheet",
    "{title}, see the drawing notes for sizes",
)


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


def documented(spec: Spec, rng: random.Random) -> tuple[Prompt, Grounding, Design]:
    doc = f"d{rng.getrandbits(48):012x}"
    facts: list[Fact] = []
    params = []
    for i, p in enumerate(spec.design.params):
        if p.provenance.source != "prompt":
            params.append(p)
            continue
        lines = [t for _, t in spec.statements]
        n = next((k for k, t in enumerate(lines) if p.provenance.quote and p.provenance.quote in t), 0)
        slug = "_".join(re.findall(r"[a-z]+", p.description.lower())[:3])
        fact = _fact(doc, i, "parameter", f"req_{n + 1}_{slug}", p.value, f"REQ-{n + 1} {lines[n]}", unit=p.unit)
        facts.append(fact)
        params.append(p.model_copy(update={"provenance": Provenance(source="document", ref=fact.id, quote=fact.text)}))
    pack = ContextPack(query=spec.title, chunks=[], facts=facts, rules=list(RULES.rules), similar_parts=[], conventions=[])
    request = rng.choice(DOC_REQUESTS).format(title=spec.title.lower())
    design = spec.design.model_copy(update={"params": params})
    return Prompt("documented", request[0].upper() + request[1:]), Grounding(pack=pack, rules=RULES), design


def _fact(doc: str, i: int, kind: str, name: str, value: float, text: str, count: int | None = None, unit: str = "mm") -> Fact:
    source = Provenance(source="document", ref=f"{doc}#p1:l{i + 2}", quote=text)
    return Fact(
        id=f"{doc}:1.{i + 2}.0",
        doc_id=doc,
        kind=kind,
        name=name,
        value=value,
        unit=unit,
        count=count,
        page=1,
        line=i + 2,
        text=text,
        source=source,
    )
