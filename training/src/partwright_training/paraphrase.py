import hashlib
import json
import re
import threading
from pathlib import Path

from partwright_agent import LLM, Message
from partwright_ir import Design, Provenance
from partwright_training.spec import num

REGISTERS = {
    "terse": "Rewrite it the way a busy engineer types a quick request: short and lowercase, with abbreviations like thk, dia, w/",
    "chatty": "Rewrite it as a friendly, slightly rambling message from a maker describing what they need and why.",
    "engineer": "Rewrite it as a precise request from a mechanical engineer, in your own sentence structure and ordering.",
    "messy": (
        "Rewrite it as a real customer would: reorder the details, mix 120x80, 120 by 80 and words, "
        "and call the part by a looser everyday name (bracket, mount, holder, plate, block, adapter)."
    ),
}
VAGUE = (
    "Rewrite it as a short, vague request from someone who does not know the sizes: say what kind of part it is and its main features, "
    "but give no numbers, sizes, thread sizes or units at all."
)
SYSTEM = (
    "You rewrite requests for mechanical parts. Keep every number exactly as written, with its meaning, and do not add numbers. "
    "Answer with the rewritten request only."
)
WORDS = dict(
    zip(("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"), range(1, 13), strict=True)
)
SIZE = re.compile(r"\bM\d+(?:\.\d+)?(?:x\d+(?:\.\d+)?)?\b", re.IGNORECASE)
LABEL = re.compile(r"\bREQ-\d+", re.IGNORECASE)
NUMBER = re.compile(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])")
PREFIXED = re.compile(r"\b[MR](\d+(?:\.\d+)?)")
TOKEN = re.compile(r"[a-zø]+|\d+(?:\.\d+)?")
UNITS = frozenset(("mm", "millimetre", "millimetres", "millimeter", "millimeters", "deg", "degrees"))
# dimension words a number belongs to; prefixes and shorthands map to one key
KEYS = {"r": "radius"}
KEYS |= {"thk": "thick", "thic": "thick", "dia": "diam", "diam": "diam", "ø": "diam", "od": "diam", "bore": "bore", "id": "bore"}
KEYS |= {"len": "long", "leng": "long", "long": "long", "wide": "wide", "widt": "wide", "high": "high", "heig": "high", "tall": "high"}
KEYS |= {"deep": "deep", "dept": "deep", "pitc": "pitch", "apar": "spacing", "spac": "spacing", "edge": "edge", "marg": "edge"}
KEYS |= {"radi": "radius", "cham": "chamfer", "fill": "fillet", "circ": "circle", "flan": "flange", "wall": "wall", "pock": "pocket"}
UNIT_TAIL = re.compile(r"\s?(?:mm|millimetres?|millimeters?|deg|degrees|°)?\s?\w*")


def numbers(text: str) -> set[float]:
    text = LABEL.sub("", text)
    found = {float(n) for n in NUMBER.findall(text)} | {float(n) for n in PREFIXED.findall(text)}
    return found | {float(v) for w, v in WORDS.items() if re.search(rf"\b{w}\b", text, re.IGNORECASE)}


class Paraphraser:
    def __init__(self, llm: LLM, cache: Path) -> None:
        self.llm = llm
        self.cache = cache
        self._lock = threading.Lock()
        self._done: dict[str, str] = {}
        if cache.exists():
            for line in cache.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self._done[row["key"]] = row["text"]

    def rewrite(self, text: str, register: str, seed: int) -> str | None:
        out = self._ask(text, REGISTERS[register], seed)
        kept = {m.upper() for m in SIZE.findall(text)} <= {m.upper() for m in SIZE.findall(out)}
        return out if kept and numbers(out) <= numbers(text) and "`" not in out else None

    def vague(self, text: str, seed: int) -> str | None:
        out = self._ask(text, VAGUE, seed)
        echoed = re.search(r"\b(omit|measurements?|units?|no numbers)\b", out, re.IGNORECASE)
        return out if not re.search(r"\d", out) and not echoed and 3 <= len(out.split()) <= 60 else None

    def _ask(self, text: str, instruction: str, seed: int) -> str:
        key = hashlib.sha1(f"{instruction}\n{text}\n{seed}".encode()).hexdigest()
        with self._lock:
            if key in self._done:
                return self._done[key]
        messages = [Message(role="system", content=SYSTEM), Message(role="user", content=f"{instruction}\n\nRequest:\n{text}")]
        out = self.llm.chat(messages, None, seed, 0.8).strip().strip('"')
        with self._lock:
            self._done[key] = out
            with self.cache.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "text": out}) + "\n")
        return out


def requote(design: Design, original: str, text: str) -> Design | None:
    params = []
    for p in design.params:
        if p.provenance.source != "prompt":
            params.append(p)
            continue
        quote = _quote(p.value, text)
        if quote is None or not _same_meaning(p.value, p.unit, original, text):
            return None
        params.append(p.model_copy(update={"provenance": Provenance(source="prompt", quote=quote)}))
    return design.model_copy(update={"params": params})


def defaults(design: Design) -> Design:
    params = [p.model_copy(update={"provenance": Provenance(source="default")}) for p in design.params]
    return design.model_copy(update={"params": params})


def _quote(value: float, text: str) -> str | None:
    options = [re.escape(num(value)), *(w for w, v in WORDS.items() if v == value)]
    m = re.search(rf"(?<![\d.])(?:{'|'.join(options)})(?![\d.])", LABEL.sub(lambda r: " " * len(r[0]), text), re.IGNORECASE)
    if m is None:
        return None
    tail = UNIT_TAIL.match(text, m.end())
    return text[m.start() : tail.end() if tail else m.end()].strip()


def _same_meaning(value: float, unit: str, original: str, text: str) -> bool:
    (was_after, was_before), (now_after, now_before) = _keys(value, original), _keys(value, text)
    if unit == "":
        return True
    if was_after and now_after:
        return was_after == now_after
    return not (was_before and now_before) or was_before == now_before


def _keys(value: float, text: str) -> tuple[str | None, str | None]:
    tokens = [t for t in TOKEN.findall(LABEL.sub("", text).lower()) if t not in UNITS]
    targets = {num(value), *(w for w, v in WORDS.items() if v == value)}
    i = next((k for k, t in enumerate(tokens) if t in targets), None)
    if i is None:
        return None, None
    return _first(tokens[i + 1 : i + 3]), _first(tokens[max(i - 2, 0) : i][::-1])


def _first(tokens: list[str]) -> str | None:
    for t in tokens:
        if t[0].isdigit():
            return None
        if key := _key(t):
            return key
    return None


def _key(token: str) -> str | None:
    return KEYS.get(token) or KEYS.get(token[:4])
