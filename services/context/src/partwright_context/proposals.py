import re
from collections.abc import Callable, Sequence

from partwright_context.facts import slug
from partwright_context.models import Fact, ProposedFact
from partwright_context.parsed import Line
from partwright_context.quantities import NUM, PINT, normalise, number
from partwright_ir import Provenance

Propose = Callable[[str], list[ProposedFact]]


def grounded(doc_id: str, lines: Sequence[Line], proposals: Sequence[ProposedFact], existing: Sequence[Fact]) -> list[Fact]:
    out: list[Fact] = []
    for i, p in enumerate(proposals):
        line = next((x for x in lines if _norm(p.quote) and _norm(p.quote) in _norm(x.text)), None)
        if line is None or (p.unit and p.unit not in PINT) or p.value not in {number(n) for n in re.findall(NUM, p.quote)}:
            continue
        value, unit = normalise(p.value, p.unit) if p.unit else (p.value, "")
        if any(f.page == line.page and f.line == line.number and f.value == value for f in [*existing, *out]):
            continue
        out.append(
            Fact(
                id=f"{doc_id}:{line.page}.{line.number}.llm{i}",
                doc_id=doc_id,
                kind="parameter",
                name=slug(p.name) or "value",
                value=value,
                unit=unit,
                page=line.page,
                line=line.number,
                text=line.text.strip(),
                source=Provenance(source="document", ref=f"{doc_id}#p{line.page}:l{line.number}", quote=p.quote[:160]),
            )
        )
    return out


def _norm(text: str) -> str:
    return " ".join(text.lower().split())
