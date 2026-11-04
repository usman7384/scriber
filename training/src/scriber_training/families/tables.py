import math
import random
from typing import Any

from scriber_training.holes import DIA
from scriber_training.spec import Draft, Position, Spec, finish, num, pick, rect_sketch

DIAMETERS = (3.4, 4.5, 5.5, 6.6, 9.0, 11.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0)
TITLES = ("Drilled plate", "Mounting plate", "Panel", "Adapter plate", "Interface plate", "Base plate", "Cover plate")
FORMATS = ("markdown", "csv", "list", "grouped")
CORNER = ("measured from the lower-left corner", "X and Y from the bottom-left corner", "origin at the lower left corner of the plate")
CENTRE = ("measured from the plate centre", "X and Y from the centre of the plate", "origin at the middle of the plate")


def table(rng: random.Random) -> Spec:
    d = Draft(rng.choice(TITLES), "table")
    length, width, thick = pick(rng, 80, 220, 5), pick(rng, 50, 150, 5), pick(rng, 3, 12)
    size = f"{num(length)} x {num(width)} x {num(thick)} mm"
    d.param("plate_length", length, "mm", "plate length along X", size)
    d.param("plate_width", width, "mm", "plate width along Y", size)
    d.param("thickness", thick, "mm", "plate thickness", size)
    d.say("Overall dimensions", f"{d.title} {size}")
    sizes = rng.sample([v for v in DIAMETERS if 3 * v <= min(length, width) / 2], rng.choice((1, 2, 2, 3)))
    holes = _layout(rng, length, width, sizes, rng.randint(4, 12))
    centred = rng.random() < 0.25
    shift = (length / 2, width / 2) if centred else (0.0, 0.0)
    rows = [(f"H{i}", x - shift[0], y - shift[1], dia) for i, (x, y, dia) in enumerate(holes, 1)]
    text, quotes = _table(rng, rows, rng.choice(FORMATS), rng.choice(CENTRE if centred else CORNER))
    d.say("Holes and ports", text)
    center: tuple[Any, Any] = (0, 0) if centred else ("plate_length / 2", "plate_width / 2")
    d.sketches.append(rect_sketch("outline", "plate_length", "plate_width", center=list(center)))
    plate = {
        "kind": "extrude",
        "id": "plate",
        "name": "Plate",
        "sketch": "outline",
        "distance": "thickness",
        "intent": "the plate the holes are drilled in",
    }
    d.features.append(plate)
    groups = sorted({r[3] for r in rows})
    for k, dia in enumerate(groups, 1):
        name = "hole_diameter" if len(groups) == 1 else f"hole_diameter_{k}"
        d.param(name, dia, "mm", f"diameter of the {num(dia)} mm holes", quotes[dia])
        points = [[_n(x), _n(y)] for _, x, y, hd in rows if hd == dia]
        at = {"kind": "points", "points": points}
        hid = "holes" if len(groups) == 1 else f"holes_{k}"
        d.features.append(
            {
                "kind": "hole",
                "id": hid,
                "name": f"{num(dia)} mm holes",
                "plane": {"ref": "plate.top"},
                "at": at,
                "diameter": name,
                "intent": "positions from the hole table",
            }
        )
        n = len(points)
        d.need("holes", f"{n} x {num(dia)} holes", count=n, diameter_min=dia - 0.05, diameter_max=dia + 0.05)
    d.positions = holes
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"thickness {num(thick)}", value=thick)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _n(v: float) -> float | int:
    return int(v) if v == int(v) else v


def _layout(rng: random.Random, length: float, width: float, sizes: list[float], n: int) -> list[Position]:
    holes: list[Position] = []
    for _ in range(n * 30):
        if len(holes) == n:
            break
        dia = rng.choice(sizes)
        # the default rule keeps each hole 1.5 x its diameter from the edges; neighbours keep a 3 mm web
        edge = 5 * math.ceil(1.5 * dia / 5)
        x, y = pick(rng, edge, 5 * math.floor((length - edge) / 5), 5), pick(rng, edge, 5 * math.floor((width - edge) / 5), 5)
        if min(x, length - x, y, width - y) < 1.5 * dia:
            continue
        if all(math.dist((x, y), (hx, hy)) >= (dia + hd) / 2 + 3 for hx, hy, hd in holes):
            holes.append((x, y, dia))
    return sorted(holes, key=lambda h: (h[1], h[0]))


def _table(rng: random.Random, rows: list[tuple[str, float, float, float]], style: str, datum: str) -> tuple[str, dict[float, str]]:
    quotes: dict[float, str] = {}
    if style == "markdown":
        lines = [f"Hole table ({datum}, mm):", "", "| Hole | X | Y | Dia |", "|---|---|---|---|"]
        for label, x, y, dia in rows:
            lines.append(f"| {label} | {num(x)} | {num(y)} | {num(dia)} |")
            quotes.setdefault(dia, lines[-1])
        return "\n".join(lines), quotes
    if style == "csv":
        lines = [f"Holes, {datum}:", "id,x,y,d"]
        for label, x, y, dia in rows:
            lines.append(f"{label},{num(x)},{num(y)},{num(dia)}")
            quotes.setdefault(dia, lines[-1])
        return "\n".join(lines), quotes
    if style == "list":
        items = []
        for label, x, y, dia in rows:
            items.append(f"{label} at ({num(x)}, {num(y)}) {DIA}{num(dia)}")
            quotes.setdefault(dia, items[-1])
        return f"through holes, {datum}: " + "; ".join(items), quotes
    parts = []
    for dia in sorted({r[3] for r in rows}):
        at = ", ".join(f"({num(x)}, {num(y)})" for _, x, y, hd in rows if hd == dia)
        parts.append(f"{num(dia)} mm holes at {at}")
        quotes[dia] = f"{num(dia)} mm holes at"
    return f"through holes, {datum}: " + "; ".join(parts), quotes
