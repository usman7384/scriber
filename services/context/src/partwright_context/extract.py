import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from partwright_context.chunking import chunk
from partwright_context.facts import line_facts
from partwright_context.models import Chunk, Document, Fact
from partwright_context.parsed import Line, Parsed
from partwright_context.proposals import Propose, grounded
from partwright_context.readers import CAD, Describe, kind_of, read
from partwright_context.rule_text import extract_rule, sentences
from partwright_context.tables import hole_facts
from partwright_ir import Rule

CONVENTION = re.compile(r"best[\s_-]?practice|convention|guideline|house[\s_-]?style|how[\s_-]?we", re.IGNORECASE)
RuleAt = tuple[str, Rule, Line]


@dataclass(frozen=True, slots=True)
class Extracted:
    doc: Document
    parsed: Parsed
    chunks: list[Chunk]
    facts: list[Fact]
    rules: list[RuleAt]


def process(path: Path, digest: str, describe: Describe | None, propose: Propose | None) -> Extracted:
    kind = kind_of(path)
    doc_id = f"d{digest[:12]}"
    parsed = read(path, kind, describe)
    chunks = chunk(doc_id, parsed.lines)
    facts, rules = ([], []) if kind in CAD else extract(doc_id, parsed)
    if propose is not None and kind not in CAD:
        facts += propose_facts(doc_id, parsed, chunks, facts, propose)
    role = "convention" if is_convention(path.name, parsed) else "spec"
    doc = Document(
        id=doc_id,
        name=path.name,
        kind=kind,
        role=role,
        sha256=digest,
        pages=parsed.pages,
        chunks=len(chunks),
        facts=len(facts),
        rules=len(rules),
        descriptor=parsed.descriptor,
    )
    return Extracted(doc, parsed, chunks, facts, rules)


def extract(doc_id: str, parsed: Parsed) -> tuple[list[Fact], list[RuleAt]]:
    facts = [f for line in parsed.lines for f in line_facts(doc_id, line)]
    facts += [f for table in parsed.tables for f in hole_facts(doc_id, table)]
    rules = []
    for line, sentence in sentences(parsed.lines):
        rule = extract_rule(doc_id, line, sentence)
        if rule is not None:
            rules.append((f"{doc_id}:{line.page}.{line.number}.{rule.id}", rule, line))
    return facts, rules


def propose_facts(doc_id: str, parsed: Parsed, chunks: Sequence[Chunk], facts: list[Fact], propose: Propose) -> list[Fact]:
    found: list[Fact] = []
    for c in chunks:
        lines = [x for x in parsed.lines if x.page == c.page and c.line_start <= x.number <= c.line_end]
        found += grounded(doc_id, lines, propose(c.text), [*facts, *found])
    return found


def is_convention(name: str, parsed: Parsed) -> bool:
    first = next((x.text for x in parsed.lines if x.text.strip()), "")
    return bool(CONVENTION.search(name) or CONVENTION.search(first))
