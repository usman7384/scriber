import random
from typing import Any

from partwright_ir.fasteners import boss_diameter, screw_holes
from partwright_training.spec import Draft, Spec, finish, num, pick

TITLES = ("Electronics enclosure", "Enclosure", "Project box", "Junction box", "Sensor housing", "Controller box")
FLOOR = {"ref": "XY", "offset": "floor"}
WALLS = (2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)


def enclosure(rng: random.Random) -> Spec:
    d = Draft(rng.choice(TITLES), "enclosure")
    screw = rng.choice(("M2.5", "M3", "M3", "M4", None))
    _, pilot, clear = screw_holes(screw) if screw else (0.0, 0.0, 0.0)
    boss = boss_diameter(screw) if screw else 0.0
    wall = rng.choice(WALLS)
    w, dep, h = pick(rng, 60, 200, 5), pick(rng, 40, 150, 5), pick(rng, 25, 80, 5)
    floor, lid_t, lip = pick(rng, 2, 4, 0.5), pick(rng, 2, 4, 0.5), pick(rng, 3, 8)
    size = f"{num(w)} x {num(dep)} x {num(h)} mm"
    d.param("width", w, "mm", "outside width", size)
    d.param("depth", dep, "mm", "outside depth", size)
    d.param("height", h, "mm", "box height without the lid", size)
    d.param("wall", wall, "mm", "wall thickness", f"{num(wall)} mm walls")
    d.param("floor", floor, "mm", "floor thickness", f"{num(floor)} mm floor")
    d.param("lid_thickness", lid_t, "mm", "lid plate thickness", f"{num(lid_t)} mm thick lid")
    d.param("lip_height", lip, "mm", "depth of the lid's locating lip", f"{num(lip)} mm lip")
    d.say("Overall dimensions", f"{d.title}, box {size} outside, {num(wall)} mm walls, {num(floor)} mm floor")
    d.say("Features", f"a separate {num(lid_t)} mm thick lid with a {num(lip)} mm lip that locates inside the walls")
    shell: dict[str, Any] = {"kind": "shell_with_lid", "id": "shell", "name": "Box", "width": "width", "depth": "depth", "height": "height"}
    shell |= {"wall": "wall", "floor": "floor", "lid_thickness": "lid_thickness", "lip_height": "lip_height", "screw": screw}
    if rng.random() < 0.3:
        gap = rng.choice((0.1, 0.3, 0.4))
        d.param("lid_clearance", gap, "mm", "clearance around the lid lip", f"{num(gap)} mm clearance")
        d.say("Features", f"{num(gap)} mm clearance around the lip")
        shell["clearance"] = "lid_clearance"
    box_features = [shell | {"intent": "the body that holds the electronics"}]
    if screw:
        # where the shell sets the screws: (wall + boss) / 2 in, and at least 1.5 clearance diameters
        inset = max((wall + boss) / 2, 1.5 * clear)
        spacing = (w - 2 * inset, dep - 2 * inset)
        d.say("Holes and ports", f"four {screw} screws through the lid into corner bosses")
        d.need("holes", f"four {screw} lid holes", count=4, diameter_min=clear - 0.1, diameter_max=clear + 0.1)
        d.need("holes", f"four {screw} pilot holes", count=4, diameter_min=pilot - 0.05, diameter_max=pilot + 0.05)
        d.need("hole_spacing", f"screws {num(spacing[0])} apart", value=spacing[0], diameter_min=clear - 0.1, diameter_max=clear + 0.1)
    else:
        d.say("Holes and ports", "no screws; the lid is a push fit")
    room = (w - 2 * wall - 2 * boss - 16, dep - 2 * wall - 2 * boss - 16)
    if min(room) >= 20 and h - floor - lip >= 10 and rng.random() < 0.5:
        box_features.append(_pcb_bosses(d, rng, room, h - floor - lip - 3, pilot))
    d.parts = [
        {"id": "box", "name": "Box", "sketches": [], "features": box_features},
        {"id": "lid", "name": "Lid", "sketches": [], "features": [{"kind": "lid", "id": "lid", "name": "Lid", "of": "box"}]},
    ]
    d.parts[1]["features"][0]["intent"] = "closes the box and seats on its rim"
    d.need("extent", f"width {num(w)}", value=w)
    d.need("extent", f"depth {num(dep)}", value=dep)
    d.need("extent", f"closed height {num(h + lid_t)}", value=h + lid_t)
    finish(d, rng, "any")
    for part in d.parts:
        if d.material:
            part["material"] = d.material
    return d.spec()


def _pcb_bosses(d: Draft, rng: random.Random, room: tuple[float, float], tall: float, screw_pilot: float) -> dict[str, Any]:
    sx, sy = pick(rng, 20, room[0], 1), pick(rng, 20, room[1], 1)
    dia, pilot = rng.choice([s for s in ((5.0, 2.2), (6.0, 2.5), (7.0, 3.2)) if s[1] != screw_pilot])
    height = pick(rng, 3, min(tall, 12), 1)
    d.param("pcb_spacing_x", sx, "mm", "board hole centres along X", f"{num(sx)} x {num(sy)} mm")
    d.param("pcb_spacing_y", sy, "mm", "board hole centres along Y", f"{num(sx)} x {num(sy)} mm")
    d.param("standoff_diameter", dia, "mm", "board standoff diameter", f"{num(dia)} mm standoffs")
    d.param("standoff_height", height, "mm", "board standoff height", f"{num(height)} mm tall")
    d.param("standoff_pilot", pilot, "mm", "pilot hole in each standoff", f"{num(pilot)} mm pilot holes")
    sizes = f"{num(dia)} mm standoffs {num(height)} mm tall with {num(pilot)} mm pilot holes"
    d.say("Features", f"four {sizes} on the floor for a circuit board with holes on {num(sx)} x {num(sy)} mm")
    d.need("holes", f"four {num(pilot)} standoff holes", count=4, diameter_min=pilot - 0.05, diameter_max=pilot + 0.05)
    at = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "pcb_spacing_x", "spacing_y": "pcb_spacing_y"}
    bosses = {"kind": "boss_pattern", "id": "pcb_standoffs", "name": "Board standoffs", "plane": FLOOR, "at": at}
    return bosses | {
        "diameter": "standoff_diameter",
        "height": "standoff_height",
        "hole_diameter": "standoff_pilot",
        "intent": "hold the circuit board off the floor",
    }
