import random
from typing import Any

from partwright_training.fasteners import edge
from partwright_training.holes import bore, need_bores
from partwright_training.spec import Draft, Spec, finish, hole, num, pick, rect_sketch

# deep-groove ball bearings: outside diameter, width (ISO 15), and an internal retaining-ring groove (width, depth)
BEARINGS = {
    "6201": (32, 10, 1.3, 0.85),
    "6202": (35, 11, 1.6, 1.0),
    "6203": (40, 12, 1.85, 1.25),
    "6204": (47, 14, 1.85, 1.25),
    "6205": (52, 15, 2.15, 1.5),
    "6206": (62, 16, 2.15, 1.5),
}
FLOOR = {"ref": "XY", "offset": "wall"}


def housing(rng: random.Random) -> Spec:
    return _bearing_block(rng) if rng.random() < 0.45 else _ribbed(rng)


def _ribbed(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Gearbox housing", "Ribbed housing", "Motor housing", "Housing", "Ribbed tray", "Pump housing")), "housing")
    length, width, height = pick(rng, 90, 200, 5), pick(rng, 60, 140, 5), pick(rng, 30, 70, 5)
    wall = pick(rng, 3, 5)
    size = f"{num(length)} x {num(width)} x {num(height)} mm"
    d.param("length", length, "mm", "outside length", size)
    d.param("width", width, "mm", "outside width", size)
    d.param("height", height, "mm", "outside height", size)
    d.param("wall", wall, "mm", "wall and floor thickness", f"{num(wall)} mm walls")
    d.say("Overall dimensions", f"{d.title}, open top, {size} outside, {num(wall)} mm walls and floor")
    d.sketches.append(rect_sketch("outline", "length", "width"))
    d.features.append({"kind": "extrude", "id": "box", "name": "Outer block", "sketch": "outline", "distance": "height"})
    shell = {"kind": "shell", "id": "hollow", "name": "Shell", "thickness": "wall", "open": [{"normal": "+z", "extreme": "max"}]}
    d.features.append(shell | {"intent": "hollows the housing to hold the mechanism"})
    for c in (("length", length), ("width", width), ("height", height)):
        d.need("extent", f"{c[0]} {num(c[1])}", value=c[1])
    pilot, boss = rng.choice(((2.5, 7.0), (3.3, 8.0), (4.2, 10.0), (5.0, 12.0)))
    inset = pick(rng, max(wall + boss / 2, 1.5 * pilot + 1), wall + boss, 0.5)
    sx, sy = length - 2 * inset, width - 2 * inset
    deep = height - wall
    tall = pick(rng, 6, max(6, deep - 4), 1)
    d.param("boss_diameter", boss, "mm", "screw boss diameter", f"{num(boss)} mm diameter")
    d.param("boss_height", tall, "mm", "boss height above the floor", f"{num(tall)} mm high")
    d.param("pilot_diameter", pilot, "mm", "pilot hole for the cover screws", f"{num(pilot)} mm pilot holes")
    d.param("boss_spacing_x", sx, "mm", "boss centre distance along X", f"on {num(sx)} x {num(sy)} mm centres")
    d.param("boss_spacing_y", sy, "mm", "boss centre distance along Y", f"on {num(sx)} x {num(sy)} mm centres")
    sizes = f"{num(boss)} mm diameter, {num(tall)} mm high, with {num(pilot)} mm pilot holes"
    d.say("Features", f"four screw bosses on the floor, {sizes}, on {num(sx)} x {num(sy)} mm centres")
    _ribs(d, rng, sx, deep)
    at = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "boss_spacing_x", "spacing_y": "boss_spacing_y"}
    bosses = {"kind": "boss_pattern", "id": "bosses", "name": "Screw bosses", "plane": FLOOR, "at": at, "diameter": "boss_diameter"}
    bosses |= {"height": "boss_height", "hole_diameter": "pilot_diameter", "intent": "take the cover screws"}
    d.features.append(bosses)
    d.need("holes", f"four {num(pilot)} pilot holes", count=4, diameter_min=pilot - 0.1, diameter_max=pilot + 0.1)
    d.need("hole_spacing", f"bosses {num(sx)} apart", value=sx, diameter_min=pilot - 0.1, diameter_max=pilot + 0.1)
    d.need("hole_spacing", f"bosses {num(sy)} apart", value=sy, diameter_min=pilot - 0.1, diameter_max=pilot + 0.1)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _ribs(d: Draft, rng: random.Random, sx: float, deep: float) -> None:
    n = rng.choice((1, 2, 3))
    gap = pick(rng, 15, max(15, sx / (n + 1)), 5)
    if (n - 1) * gap >= sx - 20:
        n = 1
    t, h = pick(rng, 2, 5), pick(rng, 5, max(5, deep * 0.6), 1)
    d.param("rib_thickness", t, "mm", "rib thickness", f"{num(t)} mm thick")
    d.param("rib_height", h, "mm", "rib height above the floor", f"{num(h)} mm high ribs")
    where = "across the middle of the floor" if n == 1 else f"across the floor, {num(gap)} mm apart, centred"
    d.say("Features", f"{('one', 'two', 'three')[n - 1]} {num(h)} mm high ribs {num(t)} mm thick {where}")
    if n > 1:
        d.param("rib_spacing", gap, "mm", "rib centre distance", f"{num(gap)} mm apart, centred")
    for i in range(n):
        c = i - (n - 1) / 2
        x: Any = 0 if c == 0 else f"{num(c)} * rib_spacing"
        rib = {
            "kind": "rib",
            "id": f"rib_{i + 1}",
            "name": f"Rib {i + 1}",
            "plane": FLOOR,
            "start": [x, "-width / 2"],
            "end": [x, "width / 2"],
        }
        d.features.append(rib | {"thickness": "rib_thickness", "height": "rib_height", "intent": "stiffens the floor between the walls"})


def _bearing_block(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Pillow block", "Bearing block", "Plummer block", "Bearing housing", "Shaft support block")), "housing")
    code = rng.choice(list(BEARINGS))
    od, bw, ring_w, ring_d = BEARINGS[code]
    rim = pick(rng, 8, 16)
    dh = od + 2 * rim
    centre = pick(rng, dh / 2 + 5, dh / 2 + 25, 1)
    base_t = pick(rng, 8, min(16, centre - dh / 2 + 4), 1)
    size = rng.choice(("M6", "M8", "M10"))
    width = pick(rng, max(bw + 6, 2 * edge(size)), max(bw, 2 * edge(size)) + 20, 1)
    length = pick(rng, dh + 4 * edge(size) + 10, dh + 4 * edge(size) + 60, 5)
    d.param("seat_diameter", od, "mm", "bearing seat diameter", f"{num(od)} mm outside diameter")
    d.param("housing_diameter", dh, "mm", "outside diameter of the bearing housing", f"{num(dh)} mm round housing")
    d.param("centre_height", centre, "mm", "shaft centre height above the base", f"{num(centre)} mm centre height")
    d.param("base_length", length, "mm", "base length", f"{num(length)} x {num(width)} mm base")
    d.param("block_width", width, "mm", "width along the shaft", f"{num(length)} x {num(width)} mm base")
    d.param("base_thickness", base_t, "mm", "base thickness", f"{num(base_t)} mm thick")
    d.say("Overall dimensions", f"{d.title} for a {code} bearing ({num(od)} mm outside diameter, {bw} mm wide)")
    d.say("Overall dimensions", f"{num(length)} x {num(width)} mm base, {num(base_t)} mm thick")
    d.say("Features", f"a {num(dh)} mm round housing on a web, {num(centre)} mm centre height, bearing seat through")
    path = {
        "kind": "path",
        "start": ["-base_length / 2", 0],
        "segments": [
            {"to": ["base_length / 2", 0]},
            {"to": ["base_length / 2", "base_thickness"]},
            {"to": ["housing_diameter / 2", "base_thickness"]},
            {"to": ["housing_diameter / 2", "centre_height"]},
            {"to": ["-housing_diameter / 2", "centre_height"], "arc": "ccw", "radius": "housing_diameter / 2"},
            {"to": ["-housing_diameter / 2", "base_thickness"]},
            {"to": ["-base_length / 2", "base_thickness"]},
        ],
    }
    d.sketches.append({"id": "profile", "plane": {"ref": "XZ"}, "entities": [path]})
    body = {"kind": "extrude", "id": "body", "name": "Block", "sketch": "profile", "extent": "symmetric", "distance": "block_width"}
    d.features.append(body | {"intent": "holds the bearing at the shaft height"})
    seat = hole("seat", "Bearing seat", "body.front", [(0, "centre_height")], diameter="seat_diameter")
    d.features.append(seat | {"intent": f"press fit for the {code} bearing's outer ring"})
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"height {num(centre + dh / 2)}", value=centre + dh / 2)
    d.need("min_holes", f"seat {num(od)}", count=1, diameter_min=od - 0.1, diameter_max=od + 0.1)
    d.take(od, od)
    spacing = pick(rng, dh + 2 * edge(size) + 2, length - 2 * edge(size), 1)
    b = bore(d, rng, size, "simple")
    d.param("mount_spacing", spacing, "mm", "mounting hole centre distance", f"{num(spacing)} mm apart")
    d.say("Holes and ports", f"two {b.words} mounting holes through the base, {num(spacing)} mm apart on the centre line")
    mounts = hole("mounts", "Mounting holes", "body.bottom", [("-mount_spacing / 2", 0), ("mount_spacing / 2", 0)], **b.spec)
    d.features.append(mounts | {"intent": "bolt the block to the frame"})
    need_bores(d, b, 2)
    d.need("hole_spacing", f"{num(spacing)} mm apart", value=spacing)
    if rng.random() < 0.4:
        at = pick(rng, 1.5, max(1.5, width - bw - ring_w - 1), 0.5)
        d.param("groove_position", at, "mm", "groove start from the front face", f"{num(at)} mm from the front face")
        d.param("groove_width", ring_w, "mm", "retaining ring groove width", f"{num(ring_w)} mm wide")
        d.param("groove_depth", ring_d, "mm", "retaining ring groove depth", f"{num(ring_d)} mm deep")
        d.say(
            "Features",
            f"a retaining-ring groove in the seat {num(ring_w)} mm wide, {num(ring_d)} mm deep, {num(at)} mm from the front face",
        )
        groove = {"kind": "groove", "id": "ring_groove", "name": "Ring groove", "of": "seat", "on": "bore", "position": "groove_position"}
        d.features.append(groove | {"width": "groove_width", "depth": "groove_depth", "intent": "holds the bearing axially with a circlip"})
    finish(d, rng, "milling_3axis")
    return d.spec()
