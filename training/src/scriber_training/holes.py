import random
from dataclasses import dataclass
from typing import Any

from scriber_training.fasteners import clearance
from scriber_training.spec import Draft, num, pick

KIND_WORDS = {"simple": "clearance", "counterbore": "counterbored", "countersink": "countersunk"}
DIA = "\N{LATIN CAPITAL LETTER O WITH STROKE}"
Extent = tuple[str, float]


@dataclass(frozen=True)
class Bore:
    words: str
    spec: dict[str, Any]
    lo: float
    hi: float

    def many(self, count: str) -> str:
        joint = " x " if count[0].isdigit() and not self.words[0].isalpha() else " "
        return f"{count}{joint}{self.words}"


def bore(d: Draft, rng: random.Random, size: str, kind: str, name: str = "hole_diameter") -> Bore:
    lo, hi = clearance(size)
    if kind != "simple" or rng.random() < 0.3:
        spec = {"fastener": size} if kind == "simple" else {"fastener": size, "type": kind}
        return Bore(f"{size} {KIND_WORDS[kind]}", spec, lo, hi)
    dia = pick(rng, lo, hi, 0.1)
    words = rng.choice((f"{num(dia)} mm", f"{num(dia)} mm dia.", f"{DIA}{num(dia)}", f"{size} clearance ({num(dia)} mm)"))
    d.param(name, dia, "mm", "hole diameter", words)
    return Bore(words, {"diameter": name}, round(dia - 0.1, 3), round(dia + 0.1, 3))


def need_bores(d: Draft, b: Bore, n: int, what: str = "holes") -> None:
    d.need("holes", f"{n} {b.words} {what}", count=n, diameter_min=b.lo, diameter_max=b.hi)


def corner_grid(d: Draft, rng: random.Random, length: Extent, width: Extent, margin: float, prefix: str) -> tuple[dict[str, Any], str]:
    (lx, lv), (wx, wv) = length, width
    sx, sy = lv - 2 * margin, wv - 2 * margin
    style = rng.choice(("margin", "inset", "centres", "centres", "square" if sx == sy else "centres"))
    if style == "square":
        words = f"on a {num(sx)} mm square"
        name = d.param(f"{prefix}_square", sx, "mm", "hole centre square", words)
        spacing = (name, name)
    elif style == "centres":
        x, y = num(sx), num(sy)
        words = rng.choice((f"on {x} x {y} mm centres", f"spaced {x} mm by {y} mm", f"{x} x {y} mm apart"))
        spacing = (
            d.param(f"{prefix}_spacing_x", sx, "mm", "hole centre distance along X", words),
            d.param(f"{prefix}_spacing_y", sy, "mm", "hole centre distance along Y", words),
        )
    else:
        words = f"{num(margin)} mm from the edges" if style == "margin" else f"{num(margin)} mm in from each edge"
        name = d.param(f"{prefix}_margin", margin, "mm", "hole centres from the edges", words)
        spacing = (f"{lx} - 2 * {name}", f"{wx} - 2 * {name}")
    d.need("hole_spacing", f"spacing {num(sx)}", value=sx)
    if sy != sx:
        d.need("hole_spacing", f"spacing {num(sy)}", value=sy)
    return {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": spacing[0], "spacing_y": spacing[1]}, words
