import math
import random
from typing import Any

from partwright_training.spec import Draft, Spec, count_word, finish, num, pick

Point = tuple[Any, Any]
TITLES = ("V-belt pulley", "Pulley", "Sheave", "Belt pulley", "Drive pulley", "V-pulley")
TAN = "sin(groove_angle / 2) / cos(groove_angle / 2)"


def pulley(rng: random.Random) -> Spec:
    d = Draft(rng.choice(TITLES), "pulley")
    n = rng.choice((1, 1, 2, 2, 3))
    od = pick(rng, 60, 200, 5)
    w, h = pick(rng, 8.5, 13, 0.5), pick(rng, 7, 11, 0.5)
    angle = rng.choice((34, 36, 38, 40))
    pitch = pick(rng, w + 3, w + 6, 0.5)
    width = pick(rng, math.ceil((n - 1) * pitch + w + 6), (n - 1) * pitch + w + 16, 1)
    bore = pick(rng, 10, min(40, od / 3), 1)
    d.param("outer_diameter", od, "mm", "outside diameter", f"{num(od)} mm outside diameter")
    d.param("pulley_width", width, "mm", "rim width", f"{num(width)} mm wide")
    d.param("bore_diameter", bore, "mm", "bore", f"{num(bore)} mm bore")
    d.take(bore, bore)
    d.say("Overall dimensions", f"{d.title}, {num(od)} mm outside diameter, {num(width)} mm wide, {num(bore)} mm bore")
    d.param("groove_width", w, "mm", "groove width at the rim", f"{num(w)} mm wide at the rim")
    d.param("groove_depth", h, "mm", "groove depth", f"{num(h)} mm deep")
    d.param("groove_angle", angle, "deg", "included groove angle", f"{angle} degree included angle")
    grooves = f"{count_word(rng, n)} V-grooves" if n > 1 else "one V-groove"
    shape = f"{num(w)} mm wide at the rim, {num(h)} mm deep, {angle} degree included angle"
    if n > 1:
        d.param("groove_pitch", pitch, "mm", "groove centre distance", f"{num(pitch)} mm apart")
        d.say("Features", f"{grooves} centred across the rim, {shape}, {num(pitch)} mm apart")
    else:
        d.say("Features", f"{grooves} centred across the rim, {shape}")
    outer: list[Point] = [("outer_diameter / 2", 0)]
    for i in range(n):
        c = i - (n - 1) / 2
        zc = "pulley_width / 2" + (f" + {num(c)} * groove_pitch" if c > 0 else f" - {num(-c)} * groove_pitch" if c < 0 else "")
        outer += [
            ("outer_diameter / 2", f"{zc} - groove_width / 2"),
            ("outer_diameter / 2 - groove_depth", f"{zc} - groove_width / 2 + groove_depth * {TAN}"),
            ("outer_diameter / 2 - groove_depth", f"{zc} + groove_width / 2 - groove_depth * {TAN}"),
            ("outer_diameter / 2", f"{zc} + groove_width / 2"),
        ]
    outer.append(("outer_diameter / 2", "pulley_width"))
    inner: list[Point] = [("bore_diameter / 2", 0)]
    length = width
    hub_room = od - 2 * h - 10
    if rng.random() < 0.5 and hub_room >= bore + 14:
        hub_d, hub_l = pick(rng, bore + 10, hub_room, 1), pick(rng, 5, 25, 1)
        d.param("hub_diameter", hub_d, "mm", "hub diameter", f"{num(hub_d)} mm hub")
        d.param("hub_length", hub_l, "mm", "hub projection", f"{num(hub_l)} mm")
        d.say("Features", f"a {num(hub_d)} mm hub projecting {num(hub_l)} mm on one side")
        inner = [("bore_diameter / 2", "-hub_length"), ("hub_diameter / 2", "-hub_length"), ("hub_diameter / 2", 0)]
        length += hub_l
    points = [*inner, *outer, ("bore_diameter / 2", "pulley_width")]
    d.sketches.append(
        {"id": "half_section", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": [list(p) for p in points]}]}
    )
    body = {"kind": "revolve", "id": "body", "name": "Pulley body", "sketch": "half_section", "axis": "Y", "angle": 360}
    d.features.append(body | {"intent": "rim grooves carry the V-belt; the bore fits the shaft"})
    d.need("extent", f"diameter {num(od)}", value=od)
    d.need("extent", f"length {num(length)}", value=length)
    if rng.random() < 0.5:
        d.say("Holes and ports", rng.choice(("DIN 6885 keyway in the bore", "a keyway in the bore to DIN 6885")))
        key = {"kind": "keyway", "id": "bore_key", "name": "Bore keyway", "of": "body", "on": "bore"}
        d.features.append(key | {"intent": "drives the pulley through a parallel key"})
    d.need("holes", f"{num(bore)} mm bore", count=1, diameter_min=bore - 0.1, diameter_max=bore + 0.1)
    finish(d, rng, "turning")
    return d.spec()
