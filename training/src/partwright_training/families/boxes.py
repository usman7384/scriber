import random

from partwright_training.fasteners import clearance, edge
from partwright_training.spec import Draft, Spec, count_word, finish, num, pick, rect_sketch


def box(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Open-top box", "Electronics box", "Tray", "Enclosure base", "Housing", "Project box")), "box")
    length = pick(rng, 40, 200, 5)
    width, height = pick(rng, 30, min(length, 150), 5), pick(rng, 15, 80, 5)
    wall = pick(rng, 1.5, min(5, width / 10), 0.5)
    size = f"{num(length)} x {num(width)} x {num(height)} mm"
    d.param("length", length, "mm", "outside length", size)
    d.param("width", width, "mm", "outside width", size)
    d.param("height", height, "mm", "outside height", size)
    d.param("wall", wall, "mm", "wall and floor thickness", f"{num(wall)} mm walls")
    d.say("Overall dimensions", f"{d.title}, outside {size}, {num(wall)} mm walls and floor, open top")
    d.sketches.append(rect_sketch("outline", "length", "width"))
    d.features.append({"kind": "extrude", "id": "box", "name": "Outer block", "sketch": "outline", "distance": "height"})
    if rng.random() < 0.5:
        r = pick(rng, 2, min(10, width / 6))
        d.param("corner_radius", r, "mm", "vertical corner radius", f"R{num(r)}")
        d.say("Finish", f"R{num(r)} on the vertical outside corners")
        d.features.append(
            {"kind": "fillet", "id": "corners", "name": "Corner radius", "edges": {"parallel": "z"}, "radius": "corner_radius"}
        )
    shell = {"kind": "shell", "id": "hollow", "name": "Shell", "thickness": "wall", "open": [{"normal": "+z", "extreme": "max"}]}
    d.features.append(shell)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"height {num(height)}", value=height)
    if rng.random() < 0.5:
        _floor_holes(d, rng, length, width, wall)
    if rng.random() < 0.35 and height >= 25:
        cw, ch = pick(rng, 8, length / 3), pick(rng, 5, height / 3)
        d.param("cutout_width", cw, "mm", "front cut-out width", f"{num(cw)} x {num(ch)} mm")
        d.param("cutout_height", ch, "mm", "front cut-out height", f"{num(cw)} x {num(ch)} mm")
        d.say("Features", f"a rectangular cut-out {num(cw)} x {num(ch)} mm through the front wall, centred, at mid-height")
        cut = rect_sketch("cutout_outline", "cutout_width", "cutout_height", plane="box.front")
        cut["entities"][0]["center"] = [0, "height / 2"]
        d.sketches.append(cut)
        d.features.append(
            {"kind": "extrude", "id": "cutout", "name": "Front cut-out", "sketch": "cutout_outline", "mode": "cut", "distance": "wall"}
        )
    finish(d, rng, "milling_3axis")
    return d.spec()


def _floor_holes(d: Draft, rng: random.Random, length: float, width: float, wall: float) -> None:
    size = rng.choice(("M3", "M4"))
    margin = pick(rng, max(wall + clearance(size)[1] / 2 + 3, edge(size)), max(10, min(20, width / 4)))
    if 2 * margin >= width - 6:
        return
    word = count_word(rng, 4)
    d.param("hole_margin", margin, "mm", "floor hole centres from the outside edges", f"{num(margin)} mm from the outside edges")
    d.say("Holes and ports", f"{word} {size} mounting holes through the floor, {num(margin)} mm from the outside edges")
    at = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "length - 2 * hole_margin", "spacing_y": "width - 2 * hole_margin"}
    d.features.append(
        {"kind": "hole", "id": "floor_holes", "name": "Floor holes", "plane": {"ref": "box.bottom"}, "at": at, "fastener": size}
    )
    lo, hi = clearance(size)
    d.need("holes", f"4 {size} floor holes", count=4, diameter_min=lo, diameter_max=hi)
    d.need("hole_spacing", f"spacing {num(length - 2 * margin)}", value=length - 2 * margin)
