import re
from collections.abc import Sequence
from typing import Literal

from scriber_context.parsed import Line
from scriber_context.quantities import NUM, TIMES, number, quantities
from scriber_ir import Process, Provenance, Rule, RuleKind

Unit = Literal["mm", "deg", ""]
RATIO = re.compile(
    rf"(?P<v>{NUM})\s*(?:[x{TIMES}*·]\s*(?:the\s+)?(?:hole\s+)?(?:d\b|dia\b|diameter|[Ø⌀])|times\s+(?:the\s+)?(?:hole\s+)?diameter|diameters?\b|d\b)",
    re.I,
)
RULE_WORDS = re.compile(
    r"\b(?:min(?:imum)?|max(?:imum)?|at least|at most|not exceed|no more than|no less than"
    r"|must|shall|should|needs?|required?|limit|within)\b|[≥≤]|>=|<="
)
DYNAMIC = re.compile(r"\b(?:should|recommended|preferabl[ey]|preferred|ideally|where possible|if possible|avoid|cost|typically)\b")
PROCESSES: list[tuple[Process, re.Pattern[str]]] = [
    ("milling_3axis", re.compile(r"mill|cnc|machin")),
    ("sla", re.compile(r"\bsla\b|resin")),
    ("sls", re.compile(r"\bsls\b|powder|sinter")),
    ("fdm", re.compile(r"\bfdm\b|\bfff\b|filament|3d[- ]?print")),
]
SIZE_WORDS = re.compile(r"overall|envelope|build volume|fit within|part size|maximum size|max(?:imum)? dimension")


SENTENCE = re.compile(r"(?:[^.;!?]|\.(?=\d))+(?:[.;!?]|$)")
CONTINUATION = re.compile(r"^[a-z0-9(Ø⌀±]")


def sentences(lines: Sequence[Line]) -> list[tuple[Line, str]]:
    out: list[tuple[Line, str]] = []
    block: list[Line] = []
    for line in lines:
        text = line.text.strip()
        joins = (
            bool(block and text and CONTINUATION.match(text)) and line.page == block[-1].page and block[-1].text.rstrip()[-1] not in ".;:!?"
        )
        if block and not joins:
            out.extend(_split(block))
            block = []
        if text:
            block.append(line)
    return [*out, *_split(block)]


def _split(block: list[Line]) -> list[tuple[Line, str]]:
    starts: list[tuple[int, Line]] = []
    text = ""
    for line in block:
        starts.append((len(text), line))
        text += line.text.strip().lstrip("#-*•| ") + " "
    found = [(m.start(), m.group().strip()) for m in SENTENCE.finditer(text)]
    return [(next(line for offset, line in reversed(starts) if offset <= start), s) for start, s in found if s]


def extract_rule(doc_id: str, line: Line, sentence: str) -> Rule | None:
    found = _kind_value(sentence)
    if found is None or not RULE_WORDS.search(sentence.lower()):
        return None
    kind, value, unit = found
    low = sentence.lower()
    process = next((p for p, pattern in PROCESSES if pattern.search(low)), "any")
    dynamic = bool(DYNAMIC.search(low))
    return Rule(
        id=kind if process == "any" else f"{kind}@{process}",
        kind=kind,
        value=value,
        unit=unit,
        process=process,
        severity="warning" if dynamic else "error",
        binding="dynamic" if dynamic else "static",
        text=sentence,
        source=Provenance(source="document", ref=f"{doc_id}#p{line.page}:l{line.number}", quote=sentence[:160]),
    )


def _kind_value(sentence: str) -> tuple[RuleKind, float, Unit] | None:
    low = sentence.lower()
    lengths = [v for v, u in quantities(sentence) if u == "mm"]
    angles = [v for v, u in quantities(sentence) if u == "deg"]
    if "overhang" in low:
        return ("max_overhang_angle", angles[0], "deg") if angles else None
    if "edge" in low and "hole" in low:
        ratio = RATIO.search(sentence)
        return ("min_hole_edge_ratio", number(ratio["v"]), "") if ratio else None
    kind: RuleKind | None = None
    if "corner" in low or ("internal" in low and "radi" in low):
        kind = "min_internal_corner_radius"
    elif "wall" in low:
        kind = "min_wall_thickness"
    elif "hole" in low and re.search(r"diameter|[ø⌀]|size", low):
        kind = "min_hole_diameter"
    elif SIZE_WORDS.search(low):
        kind = "max_overall_size"
    return (kind, lengths[0], "mm") if kind and lengths else None
