import re
from collections.abc import Callable
from typing import Any

from partwright_context.entities import materials, standards
from partwright_context.models import Fact, FactKind
from partwright_context.parsed import Line
from partwright_context.quantities import MINUS, NUM, QUANTITY, TIMES, UNIT, normalise, number
from partwright_ir import Provenance

DIA = "[Ø⌀]"
START = r"(?<![\w.])"
CALLOUT = re.compile(rf"{START}(?P<n>\d+)\s*[xX{TIMES}]\s*(?:(?P<thread>M\d+(?:\.\d+)?)(?![\d.])|{DIA}\s*(?P<d>{NUM})\s*(?P<u>{UNIT})?)")
TOL_ASYM = re.compile(
    rf"{START}(?P<dia>{DIA}\s*)?(?P<v>{NUM})\s*(?P<u1>{UNIT})?\s*\+\s*(?P<up>{NUM})\s*/?\s*[-{MINUS}]\s*(?P<lo>{NUM})\s*(?P<u2>{UNIT})?"
)
TOL = re.compile(rf"{START}(?P<dia>{DIA}\s*)?(?P<v>{NUM})\s*(?P<u1>{UNIT})?\s*(?:±|\+/-|\+-)\s*(?P<t>{NUM})\s*(?P<u2>{UNIT})?")
SIZE = re.compile(
    rf"{START}(?P<a>{NUM})\s*(?:{UNIT})?\s*[x{TIMES}]\s*(?P<b>{NUM})\s*(?:{UNIT})?(?:\s*[x{TIMES}]\s*(?P<c>{NUM}))?\s*(?P<u>{UNIT})"
)
DIAMETER = re.compile(rf"{START}{DIA}\s*(?P<v>{NUM})\s*(?P<u>{UNIT})?")
KEY_VALUE = re.compile(r"^\s*(?:[-*•]\s*)?(?P<k>[A-Za-z][\w ./()-]{0,48}?)\s*[:=]\s*(?P<v>\S.*)$")
ID_LIKE = re.compile(r"[A-Z][A-Z0-9]{1,5}-\d+[A-Z]?")
STOP = frozenset(
    {"a", "an", "the", "of", "is", "are", "be", "at", "least", "most", "to", "with", "must", "should", "shall", "not", "exceed"}
    | {"than", "by", "for", "and", "or", "in", "on", "need", "needs", "require", "requires", "have", "has", "min", "max"}
    | {"minimum", "maximum", "no", "more", "less", "use", "uses"}
)
Draft = tuple[FactKind, str, float | str, str, dict[str, Any]]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def line_facts(doc_id: str, line: Line) -> list[Fact]:
    kv = KEY_VALUE.match(line.text)
    key = kv["k"].strip() if kv else None
    offset = kv.start("v") if kv else 0
    work = " " * offset + line.text[offset:]
    drafts: list[tuple[str, Draft]] = []
    for pattern, build in EXTRACTORS:
        for m in pattern.finditer(work):
            drafts.extend((work[offset : m.start()], d) for d in build(m))
            work = work[: m.start()] + " " * (m.end() - m.start()) + work[m.end() :]
    value_text = line.text[offset:]
    drafts.extend(("", ("material", "material", name, "", {})) for name in materials(value_text))
    drafts.extend(("", ("standard", "standard", name, "", {})) for name in standards(value_text))
    if key and not drafts:
        drafts.extend(("", d) for d in _plain_value(value_text.strip()))
    source = Provenance(source="document", ref=f"{doc_id}#p{line.page}:l{line.number}", quote=line.text.strip()[:160])
    return [
        Fact(
            id=f"{doc_id}:{line.page}.{line.number}.{i}",
            doc_id=doc_id,
            kind=kind,
            name=_name(key, before, default),
            value=value,
            unit=unit,
            page=line.page,
            line=line.number,
            text=line.text.strip(),
            source=source,
            **extra,
        )
        for i, (before, (kind, default, value, unit, extra)) in enumerate(drafts)
    ]


def _callout(m: re.Match[str]) -> list[Draft]:
    if m["thread"]:
        return [("holes", m["thread"], number(m["thread"][1:]), "mm", {"count": int(m["n"])})]
    value, unit = normalise(number(m["d"]), m["u"] or "mm")
    return [("holes", "holes", value, unit, {"count": int(m["n"])})]


def _tolerance(m: re.Match[str]) -> list[Draft]:
    unit = m["u2"] or m["u1"] or ("mm" if m["dia"] else "")
    lower, upper = (number(m["lo"]), number(m["up"])) if "up" in m.groupdict() else (number(m["t"]), number(m["t"]))
    value, target = _scaled(number(m["v"]), unit)
    tol = (-_scaled(lower, unit)[0], _scaled(upper, unit)[0])
    return [("tolerance", "diameter" if m["dia"] else "dimension", value, target, {"tol": tol})]


def _size(m: re.Match[str]) -> list[Draft]:
    values = [m[g] for g in ("a", "b", "c") if m[g]]
    return [("parameter", f"size_{axis}", *normalise(number(v), m["u"]), {}) for axis, v in zip("xyz", values, strict=False)]


def _diameter(m: re.Match[str]) -> list[Draft]:
    return [("parameter", "diameter", *normalise(number(m["v"]), m["u"] or "mm"), {})]


def _quantity(m: re.Match[str]) -> list[Draft]:
    value, unit = normalise(number(m["v"]), m["u"])
    return [("parameter", {"deg": "angle", "mm": "dimension"}.get(unit, "value"), value, unit, {})]


def _scaled(value: float, unit: str) -> tuple[float, str]:
    return normalise(value, unit) if unit else (value, "")


def _plain_value(text: str) -> list[Draft]:
    if re.fullmatch(NUM, text):
        return [("parameter", "value", number(text), "", {})]
    return [("parameter", "value", text, "", {})] if 0 < len(text) <= 40 else []


def _name(key: str | None, before: str, default: str) -> str:
    clause = re.split(r"[:;,(]|\.\s|\band\b|\bor\b", before)[-1]
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z_-]+", clause) if w.lower() not in STOP][-3:]
    parts = [slug(key)] if key else []
    if not key or ID_LIKE.fullmatch(key):
        parts.append(slug(" ".join(words)))
    if default.startswith("size_") or not any(parts):
        parts.append(slug(default))
    return "_".join(p for p in parts if p)


EXTRACTORS: list[tuple[re.Pattern[str], Callable[[re.Match[str]], list[Draft]]]] = [
    (CALLOUT, _callout),
    (TOL_ASYM, _tolerance),
    (TOL, _tolerance),
    (SIZE, _size),
    (DIAMETER, _diameter),
    (QUANTITY, _quantity),
]
