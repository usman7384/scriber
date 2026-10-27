import math
import random
from typing import Any

from partwright_training.fasteners import counterbore_depth, edge, head, nominal
from partwright_training.holes import Bore, bore, corner_grid, need_bores
from partwright_training.spec import Draft, Spec, circle_sketch, count_word, finish, hole, num, pick, rect_sketch

HOLE_TYPES = ("simple", "counterbore", "countersink")


def plate(rng: random.Random) -> Spec:
    return _round_plate(rng) if rng.random() < 0.3 else _rect_plate(rng)


def _rect_plate(rng: random.Random) -> Spec:
    d = Draft(
        rng.choice(
            (
                "Mounting plate",
                "Base plate",
                "Adapter plate",
                "Cover plate",
                "Mounting bracket",
                "Motor mount",
                "Sensor holder",
                "Bracket plate",
            )
        ),
        "plate",
    )
    length, thick = pick(rng, 60, 200, 5), pick(rng, 4, 15)
    width = length if length <= 150 and rng.random() < 0.15 else pick(rng, 40, min(length, 150), 5)
    size = f"{num(length)} x {num(width)} mm"
    d.param("plate_length", length, "mm", "plate length along X", size)
    d.param("plate_width", width, "mm", "plate width along Y", size)
    d.param("thickness", thick, "mm", "plate thickness", f"{num(thick)} mm thick")
    d.say("Overall dimensions", f"{d.title} {size}, {num(thick)} mm thick")
    extra: dict[str, Any] = {}
    if rng.random() < 0.4:
        r = pick(rng, 2, min(8, width / 8))
        extra["corner_radius"] = d.param("corner_radius", r, "mm", "outline corner radius", f"R{num(r)} corners")
        d.say("Overall dimensions", f"R{num(r)} corners on the outline")
    d.sketches.append(rect_sketch("outline", "plate_length", "plate_width", **extra))
    d.features.append({"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "outline", "distance": "thickness"})
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"thickness {num(thick)}", value=thick)
    size_m = rng.choice([s for s in ("M3", "M4", "M5", "M6", "M8", "M10") if head(s) < width / 3])
    kind = _hole_type(rng, size_m, thick)
    if 2 * edge(size_m, kind) > width - 10:
        kind = "simple"
    roll = rng.random()
    if roll < 0.45:
        _corner_holes(d, rng, size_m, kind, length, width, thick)
    elif roll < 0.75 or not _hole_grid(d, rng, size_m, length, width):
        _hole_row(d, rng, size_m, kind, length, width)
    _finish_top(d, rng, thick)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _hole_type(rng: random.Random, size: str, thick: float) -> str:
    room = {"simple": 0.0, "counterbore": counterbore_depth(size) + 2, "countersink": 0.62 * nominal(size) + 2}
    options = [t for t in HOLE_TYPES if thick >= room[t]]
    if thick < 4:
        options = ["simple"]
    return rng.choice(options)


def _need_holes(d: Draft, b: Bore, size: str, kind: str, n: int) -> None:
    need_bores(d, b, n)
    if kind == "counterbore":
        d.need("counterbores", f"{n} counterbores", count=n)
        d.take(head(size), head(size) + 2.5)


def _corner_holes(d: Draft, rng: random.Random, size: str, kind: str, length: float, width: float, thick: float) -> None:
    margin = pick(rng, max(6, math.ceil(head(size) / 2 + 3), edge(size, kind)), max(8, min(20, width / 4)))
    word = count_word(rng, 4)
    b = bore(d, rng, size, kind)
    at, where = corner_grid(d, rng, ("plate_length", length), ("plate_width", width), margin, "hole")
    d.say("Holes and ports", f"{b.many(word)} holes, one in each corner, {where}")
    d.features.append({"kind": "hole", "id": "corner_holes", "name": f"{size} corner holes", "plane": {"ref": "plate.top"}, "at": at})
    d.features[-1].update(b.spec)
    _need_holes(d, b, size, kind, 4)
    if rng.random() < 0.5:
        _pocket(d, rng, size, length - 2 * margin, width - 2 * margin, thick)


def _hole_row(d: Draft, rng: random.Random, size: str, kind: str, length: float, width: float) -> None:
    n = rng.randint(2, 6)
    room = length - 2 * max(8, head(size), edge(size, kind))
    pitch = pick(rng, max(10, head(size) + 4), max(12, room / (n - 1)), 5 if room / (n - 1) > 20 else 1)
    if pitch * (n - 1) > room:
        n = 2
    word = count_word(rng, n)
    b = bore(d, rng, size, kind)
    d.param("hole_count", n, "", "number of holes in the row", b.many(word))
    d.param("hole_pitch", pitch, "mm", "hole centre distance", f"{num(pitch)} mm pitch")
    d.say("Holes and ports", f"{b.many(word)} holes in a row along the length, {num(pitch)} mm pitch, centred")
    first = hole("row_hole", f"{size} hole", "plate.top", [("-(hole_count - 1) * hole_pitch / 2", 0)], **b.spec)
    pattern = {
        "kind": "pattern",
        "id": "hole_row",
        "name": "Hole row",
        "features": ["row_hole"],
        "type": "linear",
        "count": "hole_count",
        "direction": "x",
        "spacing": "hole_pitch",
    }
    d.features += [first, pattern]
    _need_holes(d, b, size, kind, n)
    d.need("hole_spacing", f"{num(pitch)} mm pitch", value=pitch)


def _hole_grid(d: Draft, rng: random.Random, size: str, length: float, width: float) -> bool:
    room_x, room_y = length - 2 * max(8, edge(size)), width - 2 * max(8, edge(size))
    rows, cols = rng.randint(2, 3), rng.randint(2, 6)
    least = max(10, head(size) + 4)
    if room_y / (rows - 1) < least or room_x / (cols - 1) < least:
        return False
    pitch = pick(rng, least, min(60, room_x / (cols - 1)), 5 if room_x / (cols - 1) > least + 10 else 1)
    gap = pick(rng, least, min(80, room_y / (rows - 1)), 5 if room_y / (rows - 1) > least + 10 else 1)
    b = bore(d, rng, size, "simple")
    rows_words, cols_words = f"{count_word(rng, rows)} rows", f"{count_word(rng, cols)} holes per row"
    d.param("hole_columns", cols, "", "holes per row", cols_words)
    d.param("hole_rows", rows, "", "number of rows", rows_words)
    d.param("hole_pitch", pitch, "mm", "hole centre distance along each row", f"{num(pitch)} mm pitch")
    d.param("row_spacing", gap, "mm", "distance between rows", f"rows {num(gap)} mm apart")
    total = count_word(rng, rows * cols)
    where = f"{rows_words}, {cols_words}, {num(pitch)} mm pitch, rows {num(gap)} mm apart, centred"
    d.say("Holes and ports", f"{b.many(total)} holes in {where}")
    at = {"kind": "grid", "count_x": "hole_columns", "count_y": "hole_rows", "spacing_x": "hole_pitch", "spacing_y": "row_spacing"}
    d.features.append({"kind": "hole", "id": "hole_grid", "name": "Hole grid", "plane": {"ref": "plate.top"}, "at": at, **b.spec})
    need_bores(d, b, rows * cols)
    d.need("hole_spacing", f"{num(pitch)} mm pitch", value=pitch)
    d.need("hole_spacing", f"rows {num(gap)} apart", value=gap)
    return True


def _pocket(d: Draft, rng: random.Random, size: str, span_x: float, span_y: float, thick: float) -> None:
    pw, ph = span_x - head(size) - 8, span_y - head(size) - 8
    if pw < 15 or ph < 10 or thick < 6:
        return
    pw, ph = pick(rng, 15, pw), pick(rng, 10, ph)
    depth = pick(rng, 2, thick - 2.5, 0.5)
    d.param("pocket_length", pw, "mm", "pocket length", f"{num(pw)} x {num(ph)} mm")
    d.param("pocket_width", ph, "mm", "pocket width", f"{num(pw)} x {num(ph)} mm")
    d.param("pocket_depth", depth, "mm", "pocket depth", f"{num(depth)} mm deep")
    d.say("Features", f"a central rectangular pocket {num(pw)} x {num(ph)} mm, {num(depth)} mm deep, in the top face")
    d.sketches.append(rect_sketch("pocket_outline", "pocket_length", "pocket_width", plane="plate.top"))
    d.features.append(
        {"kind": "extrude", "id": "pocket", "name": "Pocket", "sketch": "pocket_outline", "mode": "cut", "distance": "pocket_depth"}
    )
    if rng.random() < 0.5:
        r = pick(rng, 1, min(4, ph / 4))
        d.param("pocket_corner_radius", r, "mm", "pocket inside corner radius", f"R{num(r)} inside corners")
        d.say("Features", f"R{num(r)} inside corners on the pocket")
        edges = {"of": "pocket", "parallel": "z", "convexity": "concave"}
        d.features.append(
            {"kind": "fillet", "id": "pocket_corners", "name": "Pocket corners", "edges": edges, "radius": "pocket_corner_radius"}
        )


def _finish_top(d: Draft, rng: random.Random, thick: float) -> None:
    if rng.random() < 0.4:
        c = rng.choice([0.5, 1.0] if thick < 8 else [0.5, 1.0, 1.5])
        d.param("edge_chamfer", c, "mm", "top edge chamfer", f"{num(c)} mm chamfer")
        d.say("Finish", f"{num(c)} mm chamfer on the top edges")
        d.features.append(
            {
                "kind": "chamfer",
                "id": "top_chamfer",
                "name": "Top chamfer",
                "edges": {"normal": "+z", "extreme": "max"},
                "length": "edge_chamfer",
            }
        )


def _round_plate(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Round cover plate", "Flange plate", "Round mounting plate", "Flange", "End cap", "Disc")), "plate")
    dia, thick = pick(rng, 60, 200, 5), pick(rng, 4, 16)
    d.param("plate_diameter", dia, "mm", "outer diameter", f"{num(dia)} mm diameter")
    d.param("thickness", thick, "mm", "plate thickness", f"{num(thick)} mm thick")
    d.say("Overall dimensions", f"{d.title}, {num(dia)} mm diameter, {num(thick)} mm thick")
    d.sketches.append(circle_sketch("disc", "plate_diameter", "XY"))
    d.features.append({"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "disc", "distance": "thickness"})
    d.need("extent", f"diameter {num(dia)}", value=dia)
    d.need("extent", f"thickness {num(thick)}", value=thick)
    size = rng.choice([s for s in ("M4", "M5", "M6", "M8", "M10", "M12") if head(s) < dia / 5])
    kind = _hole_type(rng, size, thick)
    n = rng.choice((3, 4, 5, 6, 8))
    bcd = pick(rng, max(dia * 0.5, head(size) * 3), min(dia - head(size) - 8, dia - 2 * edge(size, kind)), 5 if dia > 100 else 1)
    word = count_word(rng, n)
    b = bore(d, rng, size, kind, "bolt_hole_diameter")
    circle = rng.choice((f"{num(bcd)} mm bolt circle", f"{num(bcd)} mm PCD", f"{num(bcd)} mm pitch circle"))
    d.param("bolt_count", n, "", "number of bolt holes", b.many(word))
    d.param("bolt_circle_diameter", bcd, "mm", "bolt circle diameter", circle)
    d.say("Holes and ports", f"{b.many(word)} holes equally spaced on a {circle}")
    at = {"kind": "polar", "count": "bolt_count", "diameter": "bolt_circle_diameter"}
    d.features.append({"kind": "hole", "id": "bolt_holes", "name": f"{size} bolt holes", "plane": {"ref": "plate.top"}, "at": at})
    d.features[-1].update(b.spec)
    _need_holes(d, b, size, kind, n)
    if n % 2 == 0:
        d.need("hole_spacing", f"bolt circle {num(bcd)}", value=bcd)
    room = bcd - head(size) - 10
    centre = pick(rng, 16, room, 2)
    if room >= 16 and rng.random() < 0.6 and d.free(centre, centre):
        d.param("bore_diameter", centre, "mm", "centre bore", f"{num(centre)} mm centre bore")
        d.say("Holes and ports", f"a {num(centre)} mm centre bore through the plate")
        d.features.append(hole("bore", "Centre bore", "plate.top", [(0, 0)], diameter="bore_diameter"))
        d.need("holes", f"{num(centre)} mm bore", count=1, diameter_min=centre - 0.1, diameter_max=centre + 0.1)
    _finish_top(d, rng, thick)
    finish(d, rng, "milling_3axis")
    return d.spec()
