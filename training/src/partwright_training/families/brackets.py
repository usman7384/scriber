import random

from partwright_training.fasteners import clearance, head
from partwright_training.spec import Draft, Spec, count_word, finish, hole, num, pick


def bracket(rng: random.Random) -> Spec:
    return _angle(rng) if rng.random() < 0.6 else _channel(rng)


def _profile(d: Draft, points: list[tuple[float | str, float | str]], width: str) -> None:
    entity = {"kind": "polygon", "points": [list(p) for p in points]}
    d.sketches.append({"id": "profile", "plane": {"ref": "XZ"}, "entities": [entity]})
    d.features.append({"kind": "extrude", "id": "body", "name": "Profile", "sketch": "profile", "extent": "symmetric", "distance": width})


def _angle(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Angle bracket", "L bracket", "Corner bracket")), "bracket")
    t = pick(rng, 2, 10)
    a, b = pick(rng, 30, 120, 5), pick(rng, 25, 120, 5)
    w = pick(rng, 20, 100, 5)
    d.param("base_leg", a, "mm", "horizontal leg length", f"legs {num(a)} mm")
    d.param("upright_leg", b, "mm", "vertical leg height", f"and {num(b)} mm")
    d.param("width", w, "mm", "bracket width", f"{num(w)} mm wide")
    d.param("thickness", t, "mm", "plate thickness", f"{num(t)} mm thick")
    d.say("Overall dimensions", f"{d.title} bent from {num(t)} mm thick plate, legs {num(a)} mm and {num(b)} mm, {num(w)} mm wide")
    _profile(
        d,
        [(0, 0), ("base_leg", 0), ("base_leg", "thickness"), ("thickness", "thickness"), ("thickness", "upright_leg"), (0, "upright_leg")],
        "width",
    )
    d.need("extent", f"base leg {num(a)}", value=a)
    d.need("extent", f"upright leg {num(b)}", value=b)
    d.need("extent", f"width {num(w)}", value=w)
    if rng.random() < 0.4:
        r = pick(rng, 1, t, 0.5)
        d.param("bend_radius", r, "mm", "inside bend radius", f"R{num(r)} inside bend")
        d.say("Features", f"R{num(r)} inside bend")
        edges = {"of": "body", "parallel": "y", "convexity": "concave"}
        d.features.append({"kind": "fillet", "id": "bend", "name": "Inside bend", "edges": edges, "radius": "bend_radius"})
    sizes = [s for s in ("M4", "M5", "M6", "M8", "M10") if head(s) + 6 <= min(a, b) - t and head(s) + 4 <= w]
    if not sizes:
        return d.spec()
    size = rng.choice(sizes)
    pair = w >= 2 * head(size) + 16 and rng.random() < 0.5
    ys: list[float | str] = [0]
    if pair:
        s = pick(rng, head(size) + 6, w - head(size) - 6)
        d.param("hole_spacing", s, "mm", "spacing of the two holes in each leg", f"{num(s)} mm apart")
        ys = ["-hole_spacing / 2", "hole_spacing / 2"]
    n = len(ys)
    word = count_word(rng, n) if pair else "one"
    where = (
        f"{word} {size} clearance holes in each leg, {num(s)} mm apart" if pair else f"one {size} clearance hole in the middle of each leg"
    )
    d.say("Holes and ports", where)
    base_x, up_z = "thickness + (base_leg - thickness) / 2", "thickness + (upright_leg - thickness) / 2"
    d.features.append(hole("base_holes", "Base leg holes", "body.bottom", [(base_x, y) for y in ys], fastener=size))
    d.features.append(hole("upright_holes", "Upright leg holes", "body.left", [(y, up_z) for y in ys], fastener=size))
    lo, hi = clearance(size)
    d.need("holes", f"{2 * n} {size} holes", count=2 * n, diameter_min=lo, diameter_max=hi)
    d.need("hole_axes", "holes in both legs", count=2)
    if pair:
        d.need("hole_spacing", f"{num(s)} mm apart", value=s)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _channel(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("U channel", "Channel bracket", "Clevis bracket")), "bracket")
    t = pick(rng, 3, 10)
    a, h, w = pick(rng, 30, 120, 5), pick(rng, 20, 80, 5), pick(rng, 30, 150, 5)
    d.param("outer_width", a, "mm", "outside width across the walls", f"{num(a)} mm wide outside")
    d.param("wall_height", h, "mm", "overall height", f"{num(h)} mm high")
    d.param("length", w, "mm", "channel length", f"{num(w)} mm long")
    d.param("thickness", t, "mm", "base and wall thickness", f"{num(t)} mm walls")
    d.say("Overall dimensions", f"{d.title}, {num(a)} mm wide outside, {num(h)} mm high, {num(w)} mm long, {num(t)} mm walls and base")
    half, inner = "outer_width / 2", "outer_width / 2 - thickness"
    points: list[tuple[float | str, float | str]] = [
        (f"-{half}", 0),
        (half, 0),
        (half, "wall_height"),
        (inner, "wall_height"),
        (inner, "thickness"),
        (f"-({inner})", "thickness"),
        (f"-({inner})", "wall_height"),
        (f"-{half}", "wall_height"),
    ]
    _profile(d, points, "length")
    d.need("extent", f"width {num(a)}", value=a)
    d.need("extent", f"height {num(h)}", value=h)
    d.need("extent", f"length {num(w)}", value=w)
    sizes = [s for s in ("M4", "M5", "M6", "M8") if head(s) + 6 <= a - 2 * t]
    if sizes:
        size, n = rng.choice(sizes), rng.randint(1, 4)
        pitch = pick(rng, head(size) + 6, max(head(size) + 6, (w - 2 * head(size)) / max(n - 1, 1)), 5)
        if pitch * (n - 1) > w - 2 * head(size):
            n = 1
        word = count_word(rng, n) if n > 1 else "one"
        if n > 1:
            d.param("base_hole_count", n, "", "holes in the base", f"{word} {size}")
            d.param("base_hole_pitch", pitch, "mm", "base hole pitch", f"{num(pitch)} mm pitch")
            d.say("Holes and ports", f"{word} {size} clearance holes along the centre line of the base, {num(pitch)} mm pitch")
        else:
            d.say("Holes and ports", f"one {size} clearance hole in the centre of the base")
        start = "-(base_hole_count - 1) * base_hole_pitch / 2" if n > 1 else 0
        d.features.append(hole("base_hole", "Base hole", "body.bottom", [(0, start)], fastener=size))
        if n > 1:
            d.features.append(
                {
                    "kind": "pattern",
                    "id": "base_holes",
                    "name": "Base hole row",
                    "features": ["base_hole"],
                    "type": "linear",
                    "count": "base_hole_count",
                    "direction": "y",
                    "spacing": "base_hole_pitch",
                }
            )
            d.need("hole_spacing", f"{num(pitch)} mm pitch", value=pitch)
        lo, hi = clearance(size)
        d.need("holes", f"{n} {size} base holes", count=n, diameter_min=lo, diameter_max=hi)
    pin = pick(rng, 4, min(16, (h - t) / 2), 1)
    if rng.random() < 0.6 and d.free(pin, pin):
        d.param("pin_diameter", pin, "mm", "cross hole through both walls", f"{num(pin)} mm cross hole")
        d.say(
            "Holes and ports",
            f"a {num(pin)} mm cross hole through both walls, centred along the length, {num(h - pin)} mm above the bottom",
        )
        d.param("pin_height", h - pin, "mm", "cross hole centre above the bottom", f"{num(h - pin)} mm above the bottom")
        d.features.append(hole("pin_hole", "Cross hole", "body.right", [(0, "pin_height")], diameter="pin_diameter"))
        d.need("min_holes", f"{num(pin)} mm cross hole", count=1, diameter_min=pin - 0.1, diameter_max=pin + 0.1)
    finish(d, rng, "milling_3axis")
    return d.spec()
