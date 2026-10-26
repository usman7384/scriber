import random

from partwright_training.fasteners import clearance, edge, head
from partwright_training.spec import Draft, Spec, count_word, finish, hole, num, pick

Point = tuple[float | str, float | str]


def turned(rng: random.Random) -> Spec:
    return rng.choice((_bushing, _bushing, _shaft))(rng)


def _bushing(rng: random.Random) -> Spec:
    flanged, grooved = rng.random() < 0.5, rng.random() < 0.3
    d = Draft(
        rng.choice(("Flanged bushing", "Flanged sleeve", "Adapter"))
        if flanged
        else rng.choice(("Spacer sleeve", "Bushing", "Tube spacer", "Collar", "Sleeve")),
        "turned",
    )
    od = pick(rng, 16, 80, 2)
    bore = pick(rng, max(4, od * 0.3), od - 6, 1)
    length = pick(rng, 8, 100, 1)
    d.param("outer_diameter", od, "mm", "outside diameter", f"{num(od)} mm outside diameter")
    d.param("bore_diameter", bore, "mm", "bore diameter", f"{num(bore)} mm bore")
    d.param("length", length, "mm", "overall length", f"{num(length)} mm long")
    d.take(bore, bore)
    d.say("Overall dimensions", f"{d.title}, {num(od)} mm outside diameter, {num(bore)} mm bore, {num(length)} mm long")
    outer: list[Point] = [("outer_diameter / 2", 0)]
    max_d = od
    if flanged and length >= 8:
        fd, ft = pick(rng, od + 10, od * 2 + 20, 2), pick(rng, 3, min(12, length / 2))
        d.param("flange_diameter", fd, "mm", "flange diameter", f"{num(fd)} mm flange")
        d.param("flange_thickness", ft, "mm", "flange thickness", f"{num(ft)} mm thick")
        d.say("Features", f"a {num(fd)} mm flange {num(ft)} mm thick at the bottom end")
        outer = [("flange_diameter / 2", 0), ("flange_diameter / 2", "flange_thickness"), ("outer_diameter / 2", "flange_thickness")]
        max_d = fd
        _flange_holes(d, rng, od, fd)
    if grooved and length >= 20 and od - bore >= 6:
        g, e = pick(rng, 2, 6, 0.5), pick(rng, 0.5, min(3, (od - bore) / 4), 0.5)
        z = pick(rng, length * 0.4, length - g - 4)
        d.param("groove_width", g, "mm", "groove width", f"{num(g)} mm wide")
        d.param("groove_depth", e, "mm", "groove depth", f"{num(e)} mm deep")
        d.param("groove_position", z, "mm", "groove start from the bottom end", f"{num(z)} mm from the bottom")
        d.say("Features", f"an outside groove {num(g)} mm wide and {num(e)} mm deep, starting {num(z)} mm from the bottom")
        r, rg = "outer_diameter / 2", "outer_diameter / 2 - groove_depth"
        outer += [
            (r, "groove_position"),
            (rg, "groove_position"),
            (rg, "groove_position + groove_width"),
            (r, "groove_position + groove_width"),
        ]
    points = [("bore_diameter / 2", 0), *outer, ("outer_diameter / 2", "length"), ("bore_diameter / 2", "length")]
    _revolve(d, points)
    d.need("extent", f"diameter {num(max_d)}", value=max_d)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("holes", f"{num(bore)} mm bore", count=1, diameter_min=bore - 0.1, diameter_max=bore + 0.1)
    if not flanged:
        d.need("wall", f"wall {num((od - bore) / 2)}", value=(od - bore) / 2)
    _chamfer(d, rng, (od - bore) / 2)
    finish(d, rng, "turning")
    return d.spec()


def _flange_holes(d: Draft, rng: random.Random, od: float, fd: float) -> None:
    sizes = [
        s for s in ("M3", "M4", "M5", "M6", "M8") if head(s) + 4 <= (fd - od) / 2 and edge(s) <= (fd - od) / 4 and d.free(*clearance(s))
    ]
    if not sizes or rng.random() < 0.3:
        return
    size, n = rng.choice(sizes), rng.choice((3, 4, 6))
    bcd = round((fd + od) / 2, 1)
    word = count_word(rng, n)
    d.param("bolt_count", n, "", "number of flange holes", f"{word} {size}")
    d.param("bolt_circle_diameter", bcd, "mm", "bolt circle diameter", f"{num(bcd)} mm bolt circle")
    d.say("Holes and ports", f"{word} {size} clearance holes through the flange on a {num(bcd)} mm bolt circle")
    at = {"kind": "polar", "count": "bolt_count", "diameter": "bolt_circle_diameter"}
    d.features.append(
        {"kind": "hole", "id": "flange_holes", "name": f"{size} flange holes", "plane": {"ref": "body.bottom"}, "at": at, "fastener": size}
    )
    lo, hi = clearance(size)
    d.need("holes", f"{n} {size} flange holes", count=n, diameter_min=lo, diameter_max=hi)
    if n % 2 == 0:
        d.need("hole_spacing", f"bolt circle {num(bcd)}", value=bcd)


def _shaft(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Stepped shaft", "Stepped pin", "Shaft", "Axle", "Pin")), "turned")
    d1 = pick(rng, 12, 60, 2)
    d2 = pick(rng, 6, d1 - 4, 1)
    l1, l2 = pick(rng, 10, 80), pick(rng, 8, 60)
    d.param("major_diameter", d1, "mm", "large diameter", f"{num(d1)} mm diameter")
    d.param("major_length", l1, "mm", "length of the large diameter", f"{num(l1)} mm long")
    d.param("minor_diameter", d2, "mm", "small diameter", f"{num(d2)} mm")
    d.param("minor_length", l2, "mm", "length of the small diameter", f"{num(l2)} mm long end")
    d.say("Overall dimensions", f"{d.title}: a {num(d1)} mm diameter section {num(l1)} mm long")
    d.say("Features", f"then a {num(d2)} mm diameter, {num(l2)} mm long end on the same axis")
    points: list[Point] = [
        (0, 0),
        ("major_diameter / 2", 0),
        ("major_diameter / 2", "major_length"),
        ("minor_diameter / 2", "major_length"),
        ("minor_diameter / 2", "major_length + minor_length"),
        (0, "major_length + minor_length"),
    ]
    _revolve(d, points)
    d.need("extent", f"diameter {num(d1)}", value=d1)
    d.need("extent", f"length {num(l1 + l2)}", value=l1 + l2)
    if rng.random() < 0.5 and d2 >= 8:
        cd, depth = pick(rng, 3, d2 / 2, 0.5), pick(rng, 5, min(25, l2))
        d.param("centre_hole_diameter", cd, "mm", "centre hole in the small end", f"{num(cd)} mm centre hole")
        d.param("centre_hole_depth", depth, "mm", "centre hole depth", f"{num(depth)} mm deep")
        d.say("Holes and ports", f"a {num(cd)} mm centre hole {num(depth)} mm deep in the small end")
        d.features.append(
            hole("centre_hole", "Centre hole", "body.top", [(0, 0)], diameter="centre_hole_diameter", depth="centre_hole_depth")
        )
        d.need("holes", f"{num(cd)} mm centre hole", count=1, diameter_min=cd - 0.1, diameter_max=cd + 0.1)
    _chamfer(d, rng, d2 / 4)
    finish(d, rng, "turning")
    return d.spec()


def _revolve(d: Draft, points: list[Point]) -> None:
    d.sketches.append(
        {"id": "half_section", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": [list(p) for p in points]}]}
    )
    d.features.insert(0, {"kind": "revolve", "id": "body", "name": "Turned body", "sketch": "half_section", "axis": "Y", "angle": 360})


def _chamfer(d: Draft, rng: random.Random, room: float) -> None:
    if rng.random() < 0.5 and room >= 2:
        c = rng.choice((0.5, 1.0) if room < 4 else (0.5, 1.0, 1.5))
        d.param("edge_chamfer", c, "mm", "chamfer on the top end edges", f"{num(c)} mm chamfer")
        d.say("Finish", f"{num(c)} mm chamfer on the edges of the top end")
        d.features.append(
            {
                "kind": "chamfer",
                "id": "end_chamfer",
                "name": "End chamfer",
                "edges": {"normal": "+z", "extreme": "max"},
                "length": "edge_chamfer",
            }
        )
