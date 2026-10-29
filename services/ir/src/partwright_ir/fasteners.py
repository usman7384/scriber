import re
from dataclasses import dataclass

from partwright_ir.expr import evaluate
from partwright_ir.model import Hole

# nominal -> ISO 273 clearance (close, normal, loose), ISO 261 coarse pitch, ISO 4762 head diameter
TABLE: dict[float, tuple[tuple[float, float, float], float, float]] = {
    2: ((2.2, 2.4, 2.6), 0.4, 3.8),
    2.5: ((2.7, 2.9, 3.1), 0.45, 4.5),
    3: ((3.2, 3.4, 3.6), 0.5, 5.5),
    4: ((4.3, 4.5, 4.8), 0.7, 7.0),
    5: ((5.3, 5.5, 5.8), 0.8, 8.5),
    6: ((6.4, 6.6, 7.0), 1.0, 10.0),
    8: ((8.4, 9.0, 10.0), 1.25, 13.0),
    10: ((10.5, 11.0, 12.0), 1.5, 16.0),
    12: ((13.0, 13.5, 14.5), 1.75, 18.0),
    14: ((15.0, 15.5, 16.5), 2.0, 21.0),
    16: ((17.0, 17.5, 18.5), 2.0, 24.0),
    18: ((19.0, 20.0, 21.0), 2.5, 27.0),
    20: ((21.0, 22.0, 24.0), 2.5, 30.0),
    22: ((23.0, 24.0, 26.0), 2.5, 33.0),
    24: ((25.0, 26.0, 28.0), 3.0, 36.0),
    27: ((28.0, 30.0, 32.0), 3.0, 40.0),
    30: ((31.0, 33.0, 35.0), 3.5, 45.0),
}
FITS = ("close", "normal", "loose")
DESIGNATION = re.compile(r"^M(\d+(?:\.\d+)?)(?:x(\d+(?:\.\d+)?))?$")


@dataclass(frozen=True)
class HoleSize:
    diameter: float
    cb_diameter: float | None
    cb_depth: float | None
    cs_diameter: float | None


def parse(fastener: str) -> tuple[float, float] | None:
    m = DESIGNATION.match(fastener)
    if m is None or not 2 <= float(m[1]) <= 30:
        return None
    nominal = float(m[1])
    return nominal, float(m[2]) if m[2] else row(nominal)[1]


def row(nominal: float) -> tuple[tuple[float, float, float], float, float]:
    if nominal in TABLE:
        return TABLE[nominal]
    lo = max(k for k in TABLE if k < nominal)
    hi = min(k for k in TABLE if k > nominal)
    t = (nominal - lo) / (hi - lo)
    (a, pitch, head_a), (b, _, head_b) = TABLE[lo], TABLE[hi]
    clearance = tuple(round(x + t * (y - x), 1) for x, y in zip(a, b, strict=True))
    return (clearance[0], clearance[1], clearance[2]), pitch, round(head_a + t * (head_b - head_a), 1)


def hole_size(hole: Hole, values: dict[str, float]) -> HoleSize:
    def v(e: float | str | None) -> float | None:
        return None if e is None else evaluate(e, values)

    spec = parse(hole.fastener) if hole.fastener else None
    if hole.diameter is not None:
        diameter = evaluate(hole.diameter, values)
    elif spec is None:
        raise ValueError(f"hole {hole.id!r} needs a diameter or a known fastener such as 'M6' or 'M18x1.5'")
    else:
        nominal, pitch = spec
        diameter = round(nominal - pitch, 2) if hole.type == "tapped" else row(nominal)[0][FITS.index(hole.fit)]
    head = row(spec[0])[2] if spec else None
    cb_diameter, cb_depth = v(hole.cb_diameter), v(hole.cb_depth)
    if hole.type == "counterbore" and spec is not None and head is not None:
        # DIN 974-1 style seat for ISO 4762: head diameter plus running clearance, head height plus a little
        cb_diameter = cb_diameter or head + (1.0 if spec[0] <= 6 else 2.0)
        cb_depth = cb_depth or float(spec[0]) + 0.4
    cs = v(hole.cs_diameter)
    if hole.type == "countersink" and cs is None and spec is not None:
        cs = round(2.24 * spec[0], 2)  # ISO 10642 head diameter
    keep_cb = hole.type == "counterbore"
    return HoleSize(diameter, cb_diameter if keep_cb else None, cb_depth if keep_cb else None, cs if hole.type == "countersink" else None)


def screw_holes(screw: str) -> tuple[float, float, float]:
    spec = parse(screw)
    if spec is None:
        raise ValueError(f"unknown screw {screw!r}; use M2 to M30")
    nominal, pitch = spec
    return nominal, round(nominal - pitch, 2), row(nominal)[0][FITS.index("normal")]
