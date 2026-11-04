import random
from collections.abc import Callable
from typing import Any

from scriber_training.spec import Draft, Spec, count_word, num, pick, rect_sketch

PROFILE = "house-style.md"  # evals/parity/m5/house-style.md
WALL, BORE, BORE_DEPTH, BOSS, FILLET, EDGE = 2.5, 4.0, 6.0, 13.0, 1.0, 8.0
BOXES = ("Project enclosure", "Electronics housing", "Instrument case", "Controller box", "Sensor housing", "Battery tray")
PLATES = ("Mounting plate", "Sensor plate", "Base plate", "Adapter plate", "Fixing bar", "Display mount")
POINTS = ("{n} screw points in the corners", "{n} mounting bosses, one per corner", "fixing points at the {n} corners for a lid")
CORNERS = ("{n} mounting holes, one near each corner", "{n} fixing holes at the corners", "{n} screw holes in the corners")


def enclosure(rng: random.Random) -> Spec:
    d = Draft(rng.choice(BOXES), "house-enclosure")
    length = pick(rng, 50, 180, 5)
    width, height = pick(rng, 40, min(length, 120), 5), pick(rng, 20, 70, 5)
    size = f"{num(length)} x {num(width)} x {num(height)} mm"
    for name, value, what in (("length_mm", length, "length"), ("width_mm", width, "width"), ("height_mm", height, "height")):
        d.param(name, value, "mm", f"outside {what}", size)
        d.need("extent", f"{what} {num(value)}", value=value)
    d.rule("wall_mm", WALL, "mm", "wall and floor thickness", f"{PROFILE}#wall")
    d.say("Overall dimensions", f"{d.title}, {size} outside, open top")
    d.sketches.append(rect_sketch("outline", "length_mm", "width_mm"))
    d.features += [_extrude("body", "outline", "height_mm"), _fillet(d)]
    d.features.append(
        {"kind": "shell", "id": "hollow", "name": "Shell", "thickness": "wall_mm", "open": [{"normal": "+z", "extreme": "max"}]}
    )
    if rng.random() < 0.7:
        d.say("Features", rng.choice(POINTS).format(n=count_word(rng, 4)))
        d.rule("boss_diameter_mm", BOSS, "mm", "insert boss diameter", f"{PROFILE}#insert")
        d.sketches.append(
            {"id": "bosses", "plane": {"ref": "XY", "offset": "wall_mm"}, "entities": [_circle(*c, "boss_diameter_mm") for c in _corners()]}
        )
        d.features.append(_extrude("boss", "bosses", "height_mm - wall_mm"))
        _inserts(d, "height_mm", _grid(), 4)
    return d.spec()


def plate(rng: random.Random) -> Spec:
    d = Draft(rng.choice(PLATES), "house-plate")
    length, width, thick = pick(rng, 60, 200, 5), pick(rng, 30, 120, 5), pick(rng, 8, 14)
    size = f"{num(length)} x {num(width)} mm"
    d.param("length_mm", length, "mm", "plate length along X", size)
    d.param("width_mm", width, "mm", "plate width along Y", size)
    d.param("thickness_mm", thick, "mm", "plate thickness", f"{num(thick)} mm thick")
    for what, value in (("length", length), ("width", width), ("thickness", thick)):
        d.need("extent", f"{what} {num(value)}", value=value)
    d.say("Overall dimensions", f"{d.title} {size}, {num(thick)} mm thick")
    d.sketches.append(rect_sketch("outline", "length_mm", "width_mm"))
    d.features += [_extrude("plate", "outline", "thickness_mm"), _fillet(d)]
    room = length - 2 * EDGE
    if rng.random() < 0.5 or room < 30:
        d.say("Holes and ports", rng.choice(CORNERS).format(n=count_word(rng, 4)))
        _inserts(d, "thickness_mm", _grid(), 4)
        return d.spec()
    n = rng.randint(2, min(5, int(room // 15) + 1))
    pitch = 5 * rng.randint(3, int(room / (n - 1) // 5))
    words = f"{count_word(rng, n)} mounting holes"
    d.param("hole_count_n", n, "", "number of holes in the row", words)
    d.param("hole_pitch_mm", pitch, "mm", "hole centre distance", f"{num(pitch)} mm apart")
    d.say("Holes and ports", f"{words} in a line along the length, {num(pitch)} mm apart, centred")
    d.need("hole_spacing", f"{num(pitch)} mm pitch", value=pitch)
    _inserts(d, "thickness_mm", {"kind": "points", "points": [["-(hole_count_n - 1) * hole_pitch_mm / 2", 0]]}, n)
    d.features.append(
        {
            "kind": "pattern",
            "id": "insert_row",
            "name": "Insert row",
            "features": ["inserts"],
            "type": "linear",
            "count": "hole_count_n",
            "direction": "x",
            "spacing": "hole_pitch_mm",
        }
    )
    return d.spec()


def _inserts(d: Draft, top: str, at: dict[str, Any], n: int) -> None:
    d.rule("insert_bore_mm", BORE, "mm", "M3 heat-set insert bore", f"{PROFILE}#insert")
    d.rule("insert_depth_mm", BORE_DEPTH, "mm", "M3 heat-set insert depth", f"{PROFILE}#insert")
    if at["kind"] == "grid":
        d.rule("hole_edge_mm", EDGE, "mm", "hole centre to outside edge, 2 x D", f"{PROFILE}#edge")
    plane = {"ref": "XY", "offset": top}
    d.features.append(
        {
            "kind": "hole",
            "id": "inserts",
            "name": "M3 insert bores",
            "plane": plane,
            "at": at,
            "diameter": "insert_bore_mm",
            "depth": "insert_depth_mm",
        }
    )
    d.need("holes", f"{n} insert bores", count=n, diameter_min=BORE - 0.05, diameter_max=BORE + 0.05)


def _extrude(fid: str, sketch: str, distance: str) -> dict[str, Any]:
    return {"kind": "extrude", "id": fid, "name": fid.title(), "sketch": sketch, "distance": distance}


def _fillet(d: Draft) -> dict[str, Any]:
    d.rule("edge_fillet_mm", FILLET, "mm", "vertical outside edge fillet", f"{PROFILE}#fillet")
    return {"kind": "fillet", "id": "edge_fillet", "name": "Edge fillet", "edges": {"parallel": "z"}, "radius": "edge_fillet_mm"}


def _grid() -> dict[str, Any]:
    spacing = {"spacing_x": "length_mm - 2 * hole_edge_mm", "spacing_y": "width_mm - 2 * hole_edge_mm"}
    return {"kind": "grid", "count_x": 2, "count_y": 2, **spacing}


def _corners() -> list[tuple[str, str]]:
    x, y = "length_mm / 2 - hole_edge_mm", "width_mm / 2 - hole_edge_mm"
    return [(sx, sy) for sx in (x, f"-({x})") for sy in (y, f"-({y})")]


def _circle(x: str, y: str, diameter: str) -> dict[str, Any]:
    return {"kind": "circle", "center": [x, y], "diameter": diameter}


HOUSE: dict[str, Callable[[random.Random], Spec]] = {"house-enclosure": enclosure, "house-plate": plate}
