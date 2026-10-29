import random
from typing import Any

from partwright_ir.keys import din6885
from partwright_training.spec import Draft, Spec, finish, num, pick

Point = tuple[Any, Any]
# DIN 471 external retaining rings: shaft d -> (groove width m, groove diameter d2)
CIRCLIP = {
    12: (1.1, 11.5),
    15: (1.1, 14.3),
    17: (1.1, 16.2),
    20: (1.3, 19.0),
    25: (1.3, 23.9),
    30: (1.6, 28.6),
    35: (1.6, 33.0),
    40: (1.85, 37.5),
}
ROLES = ("journal", "bearing_seat", "gear_seat", "collar", "pulley_seat", "end")
TITLES = ("Stepped shaft", "Drive shaft", "Output shaft", "Spindle", "Gear shaft", "Idler shaft")


def shaft(rng: random.Random) -> Spec:
    d = Draft(rng.choice(TITLES), "shaft")
    n = rng.randint(2, 4)
    roles = rng.sample(ROLES, n)
    dias = sorted(rng.sample(sorted(CIRCLIP), n), reverse=rng.random() < 0.5)
    if n > 2 and rng.random() < 0.5:
        rng.shuffle(dias)
    steps = []
    for role, dia in zip(roles, dias, strict=True):
        length = pick(rng, 15, 70, 5)
        label = role.replace("_", " ")
        d.param(f"{role}_diameter", dia, "mm", f"{label} diameter", f"{label} {num(dia)} mm diameter")
        d.param(f"{role}_length", length, "mm", f"{label} length", f"{num(length)} mm long")
        steps.append((role, float(dia), length))
    words = "; ".join(f"{r.replace('_', ' ')} {num(dia)} mm diameter, {num(length)} mm long" for r, dia, length in steps)
    d.say("Overall dimensions", f"{d.title}, sections from the bottom end: {words}")
    points: list[Point] = [(0, 0)]
    z = "0"
    for role, _, _ in steps:
        points += [(f"{role}_diameter / 2", z), (f"{role}_diameter / 2", f"{z} + {role}_length".removeprefix("0 + "))]
        z = f"{z} + {role}_length".removeprefix("0 + ")
    points.append((0, z))
    section = {"id": "half_section", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": [list(p) for p in points]}]}
    d.sketches.append(section)
    body = {"kind": "revolve", "id": "body", "name": "Shaft", "sketch": "half_section", "axis": "Y", "angle": 360}
    d.features.append(body | {"intent": "carries the parts mounted on each step"})
    _keyway(d, rng, steps)
    _circlip(d, rng, steps)
    d.need("extent", f"diameter {num(max(dias))}", value=max(dias))
    d.need("extent", f"length {num(sum(s[2] for s in steps))}", value=sum(s[2] for s in steps))
    finish(d, rng, "turning")
    return d.spec()


def _start(steps: list[tuple[str, float, float]], i: int) -> tuple[str, float]:
    names = [f"{r}_length" for r, _, _ in steps[:i]]
    return " + ".join(names) or "0", sum(s[2] for s in steps[:i])


def _keyway(d: Draft, rng: random.Random, steps: list[tuple[str, float, float]]) -> None:
    # the default wall rule's probe reads the edge of a small keyway as a thin wall, so keys go on 20 mm and up
    seats = [i for i, (_, dia, length) in enumerate(steps) if dia >= 20 and length >= 20]
    if not seats or rng.random() < 0.2:
        return
    i = rng.choice(seats)
    role, dia, length = steps[i]
    start, _ = _start(steps, i)
    key_l = pick(rng, 10, length - 6, 1)
    inset = pick(rng, 2, max(2, (length - key_l) / 2), 0.5)
    d.param("keyway_length", key_l, "mm", "keyway length", f"{num(key_l)} mm long keyway")
    d.param("keyway_inset", inset, "mm", "keyway start from the step's lower end", f"{num(inset)} mm from the lower end of that step")
    where = f"{num(key_l)} mm long keyway in the {role.replace('_', ' ')}, starting {num(inset)} mm from the lower end of that step"
    key: dict[str, Any] = {"kind": "keyway", "id": "keyway", "name": "Keyway", "of": "body", "position": f"{start} + keyway_inset"}
    key = key | {"length": "keyway_length", "intent": "takes a parallel key to drive the mounted hub"}
    key["position"] = str(key["position"]).removeprefix("0 + ")
    if rng.random() < 0.5:
        d.say("Features", f"a DIN 6885 {where}")
    else:
        width, depth, _ = din6885(dia)
        d.param("keyway_width", width, "mm", "keyway width", f"{num(width)} mm wide")
        d.param("keyway_depth", depth, "mm", "keyway depth", f"{num(depth)} mm deep")
        d.say("Features", f"a {where}, {num(width)} mm wide and {num(depth)} mm deep")
        key |= {"width": "keyway_width", "depth": "keyway_depth"}
    d.features.append(key)


def _circlip(d: Draft, rng: random.Random, steps: list[tuple[str, float, float]]) -> None:
    i = rng.randrange(len(steps))
    role, dia, length = steps[i]
    if length < 15 or rng.random() < 0.3:
        return
    width, d2 = CIRCLIP[int(dia)]
    depth = round((dia - d2) / 2, 3)
    start, _ = _start(steps, i)
    at = pick(rng, 3, length - width - 3, 0.5)
    d.param("groove_position", at, "mm", "groove start from the step's lower end", f"{num(at)} mm from the lower end of the")
    d.param("groove_width", width, "mm", "retaining ring groove width", f"{num(width)} mm wide")
    d.param("groove_depth", depth, "mm", "retaining ring groove depth", f"{num(depth)} mm deep")
    label = role.replace("_", " ")
    d.say("Features", f"a circlip groove {num(width)} mm wide and {num(depth)} mm deep, {num(at)} mm from the lower end of the {label}")
    position = f"{start} + groove_position".removeprefix("0 + ")
    groove = {"kind": "groove", "id": "circlip_groove", "name": "Circlip groove", "of": "body", "position": position}
    d.features.append(
        groove | {"width": "groove_width", "depth": "groove_depth", "intent": "seats a retaining ring that locates the part axially"}
    )
