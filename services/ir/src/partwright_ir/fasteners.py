from dataclasses import dataclass

from partwright_ir.expr import evaluate
from partwright_ir.model import Hole

# ISO 273 clearance (close, normal, loose), ISO 261 tap drill, DIN 974-1 counterbore for ISO 4762 (diameter, depth),
# ISO 10642 countersunk head diameter
TABLE: dict[str, tuple[tuple[float, float, float], float, tuple[float, float], float]] = {
    "M2": ((2.2, 2.4, 2.6), 1.6, (4.4, 2.3), 4.4),
    "M2.5": ((2.7, 2.9, 3.1), 2.05, (5.5, 2.8), 5.5),
    "M3": ((3.2, 3.4, 3.6), 2.5, (6.5, 3.4), 6.72),
    "M4": ((4.3, 4.5, 4.8), 3.3, (8.0, 4.4), 8.96),
    "M5": ((5.3, 5.5, 5.8), 4.2, (10.0, 5.4), 11.2),
    "M6": ((6.4, 6.6, 7.0), 5.0, (11.0, 6.4), 13.44),
    "M8": ((8.4, 9.0, 10.0), 6.8, (15.0, 8.6), 17.92),
    "M10": ((10.5, 11.0, 12.0), 8.5, (18.0, 10.6), 22.4),
    "M12": ((13.0, 13.5, 14.5), 10.2, (20.0, 12.6), 26.88),
}
FITS = ("close", "normal", "loose")


@dataclass(frozen=True)
class HoleSize:
    diameter: float
    cb_diameter: float | None
    cb_depth: float | None
    cs_diameter: float | None


def hole_size(hole: Hole, values: dict[str, float]) -> HoleSize:
    def v(e: float | str | None) -> float | None:
        return None if e is None else evaluate(e, values)

    row = TABLE.get(hole.fastener) if hole.fastener else None
    if hole.diameter is not None:
        diameter = evaluate(hole.diameter, values)
    elif row is None:
        raise ValueError(f"hole {hole.id!r} needs a diameter or a known fastener ({', '.join(TABLE)})")
    else:
        diameter = row[1] if hole.type == "tapped" else row[0][FITS.index(hole.fit)]
    cb = (v(hole.cb_diameter), v(hole.cb_depth))
    if hole.type == "counterbore" and row is not None:
        cb = (cb[0] or row[2][0], cb[1] or row[2][1])
    cs = v(hole.cs_diameter)
    if hole.type == "countersink" and cs is None and row is not None:
        cs = row[3]
    keep_cb = hole.type == "counterbore"
    return HoleSize(diameter, cb[0] if keep_cb else None, cb[1] if keep_cb else None, cs if hole.type == "countersink" else None)
