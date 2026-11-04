import re
from typing import Literal

EntityKind = Literal["material", "standard", "designation", "fastener"]
Mention = tuple[EntityKind, str]

MATERIALS = {
    "Al 6061": re.compile(r"\b(?:AA|Al|EN\s?AW|alumini?um)\s*-?\s*6061(?:-T\d+)?\b|\b6061-T\d+\b", re.IGNORECASE),
    "Al 6082": re.compile(r"\b(?:AA|Al|EN\s?AW|alumini?um)\s*-?\s*6082(?:-T\d+)?\b|\b6082-T\d+\b", re.IGNORECASE),
    "S235": re.compile(r"\bS235(?:JR|J0|J2)?\b"),
    "S355": re.compile(r"\bS355(?:JR|J0|J2)?\b"),
    "1.4301": re.compile(r"\b1\.4301\b|\bX5CrNi18-10\b|\b(?:AISI\s*)?304\s+stainless\b|\bstainless(?:\s+steel)?\s+304\b", re.IGNORECASE),
    "PLA": re.compile(r"\bPLA\b"),
    "PETG": re.compile(r"\bPETG\b"),
    "ABS": re.compile(r"\bABS\b"),
    "PA12": re.compile(r"\bPA\s?12\b|\bnylon\s?12\b", re.IGNORECASE),
}
STANDARD = re.compile(r"\b(ISO|DIN|EN|ASME|ANSI)\s?(\d{2,5}(?:-\d+)*)\b")
DESIGNATION = re.compile(r"\b([A-Z][A-Z0-9]{1,5}-\d{1,6}[A-Z]?)\b")
FASTENER = re.compile(r"(?<![\w.])(M\d+(?:\.\d+)?)(?![\d.])")
NOT_DESIGNATION = re.compile(r"ISO|DIN|EN|AW|ASME|ANSI|M\d+")


def materials(text: str) -> list[str]:
    return [name for name, pattern in MATERIALS.items() if pattern.search(text)]


def standards(text: str) -> list[str]:
    return list(dict.fromkeys(f"{m[1]} {m[2]}" for m in STANDARD.finditer(text)))


def mentions(text: str) -> list[Mention]:
    designations = [d for d in DESIGNATION.findall(text) if not NOT_DESIGNATION.fullmatch(d.split("-")[0])]
    found: list[Mention] = [
        *(("material", m) for m in materials(text)),
        *(("standard", s) for s in standards(text)),
        *(("designation", d) for d in designations),
        *(("fastener", f) for f in FASTENER.findall(text)),
    ]
    return list(dict.fromkeys(found))
