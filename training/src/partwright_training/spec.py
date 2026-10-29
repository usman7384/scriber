import random
from dataclasses import dataclass, field
from typing import Any

from partwright_agent import Requirement
from partwright_ir import Design

SECTIONS = ("Overall dimensions", "Features", "Holes and ports", "Finish", "Manufacturing")


@dataclass(frozen=True)
class Spec:
    family: str
    title: str
    statements: tuple[tuple[str, str], ...]
    design: Design
    checks: tuple[Requirement, ...]
    exempt: tuple[str, ...] = ()

    def params(self) -> list[str]:
        return [p.name for p in self.design.params]


@dataclass
class Draft:
    title: str
    family: str
    params: list[dict[str, Any]] = field(default_factory=list)
    sketches: list[dict[str, Any]] = field(default_factory=list)
    features: list[dict[str, Any]] = field(default_factory=list)
    statements: list[tuple[str, str]] = field(default_factory=list)
    checks: list[Requirement] = field(default_factory=list)
    taken: list[tuple[float, float]] = field(default_factory=list)
    material: str | None = None
    process: str = "any"
    exempt: tuple[str, ...] = ()

    def param(self, name: str, value: float, unit: str, description: str, quote: str) -> str:
        self.params.append({"name": name, "value": value, "unit": unit, "description": description, "provenance": _prov(quote)})
        return name

    def standard(self, name: str, value: float, unit: str, description: str, ref: str) -> str:
        provenance = {"source": "standard", "ref": ref}
        self.params.append({"name": name, "value": value, "unit": unit, "description": description, "provenance": provenance})
        return name

    def rule(self, name: str, value: float, unit: str, description: str, ref: str) -> str:
        provenance = {"source": "rule", "ref": ref}
        self.params.append({"name": name, "value": value, "unit": unit, "description": description, "provenance": provenance})
        return name

    def say(self, section: str, text: str) -> None:
        assert section in SECTIONS, section
        self.statements.append((section, text))

    def need(self, kind: str, description: str, **fields: Any) -> None:
        self.checks.append(Requirement.model_validate({"kind": kind, "description": description, **fields}))
        if kind in ("holes", "min_holes"):
            self.take(fields["diameter_min"], fields["diameter_max"])

    def take(self, lo: float, hi: float) -> None:
        self.taken.append((lo, hi))

    def free(self, lo: float, hi: float) -> bool:
        return all(hi < a - 0.2 or lo > b + 0.2 for a, b in self.taken)

    def spec(self) -> Spec:
        part = {"id": "part", "name": self.title, "sketches": self.sketches, "features": self.features}
        if self.material:
            part["material"] = self.material
        if self.process != "any":
            part["process"] = self.process
        design = Design.model_validate({"ir_version": 2, "title": self.title, "params": self.params, "parts": [part]})
        return Spec(self.family, self.title, tuple(self.statements), design, tuple(self.checks), self.exempt)


def _prov(quote: str) -> dict[str, str]:
    return {"source": "prompt", "quote": quote}


def pick(rng: random.Random, lo: float, hi: float, step: float = 1.0) -> float:
    n = round((hi - lo) / step)
    return round(lo + step * rng.randint(0, max(n, 0)), 3)


def num(v: float) -> str:
    return f"{v:g}"


def hole(hid: str, name: str, plane: str, points: list[tuple[Any, Any]], **spec: Any) -> dict[str, Any]:
    at = {"kind": "points", "points": [list(p) for p in points]}
    return {"kind": "hole", "id": hid, "name": name, "plane": {"ref": plane}, "at": at, **spec}


def rect_sketch(sid: str, width: str, height: str, plane: str = "XY", **extra: Any) -> dict[str, Any]:
    return {"id": sid, "plane": {"ref": plane}, "entities": [{"kind": "rect", "width": width, "height": height, **extra}]}


def circle_sketch(sid: str, diameter: str, plane: str, center: tuple[Any, Any] = (0, 0)) -> dict[str, Any]:
    return {"id": sid, "plane": {"ref": plane}, "entities": [{"kind": "circle", "center": list(center), "diameter": diameter}]}


MATERIALS = ("aluminium 6061-T6", "steel S235", "stainless steel 304", "brass CW614N", "POM", "aluminium 7075")
WORDS = ("two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def count_word(rng: random.Random, n: int) -> str:
    return WORDS[n - 2] if 2 <= n <= 12 and rng.random() < 0.5 else str(n)


def finish(draft: Draft, rng: random.Random, process: str) -> None:
    if rng.random() < 0.5:
        draft.material = rng.choice(MATERIALS)
        draft.say("Manufacturing", f"Material: {draft.material}")
    if rng.random() < 0.4:
        draft.process = process
        draft.say("Manufacturing", "Made by CNC turning" if process == "turning" else "Made by 3-axis CNC milling")
