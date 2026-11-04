import math
import random
from typing import Any

from scriber_training.spec import Draft, Spec, finish, num, pick

# ISO 54 first-series modules
MODULES = (0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
GEAR_TITLES = ("Spur gear", "Gear", "Gear wheel", "Drive gear", "Straight-cut gear")
PAIR_TITLES = ("Spur gear pair", "Gear pair", "Gear set", "Reduction gear pair", "Meshing gears")


def gear(rng: random.Random) -> Spec:
    return _pair(rng) if rng.random() < 0.45 else _single(rng)


def _module(d: Draft, rng: random.Random) -> float:
    m = rng.choice(MODULES)
    d.param("module", m, "mm", "gear module", rng.choice((f"module {num(m)}", f"m = {num(m)}", f"{num(m)} module")))
    return m


def _wheel(d: Draft, rng: random.Random, prefix: str, m: float, z: int, width: str, **extra: Any) -> dict[str, Any]:
    name = f"{prefix}_teeth" if prefix else "teeth"
    root = m * (z - 2.5)
    # the default hole-edge rule wants the bore within a third of the root diameter
    bore = pick(rng, max(5, round(0.15 * root)), max(5, int(root / 3)), 1)
    label = f"{prefix} " if prefix else ""
    d.param(name, z, "", f"{label}tooth count".strip(), f"{z} teeth")
    bore_name = f"{prefix}_bore" if prefix else "bore_diameter"
    d.param(bore_name, bore, "mm", f"{label}bore".strip(), f"{num(bore)} mm bore")
    d.take(bore, bore)
    feature = {"kind": "spur_gear", "id": "gear", "name": f"{label.title()}Spur gear".strip(), "module": "module", "teeth": name}
    feature |= {"face_width": width, "bore": bore_name, **extra}
    d.need("holes", f"{label}bore {num(bore)}".strip(), count=1, diameter_min=bore - 0.1, diameter_max=bore + 0.1)
    return feature


def _single(rng: random.Random) -> Spec:
    d = Draft(rng.choice(GEAR_TITLES), "gear")
    m = _module(d, rng)
    z = rng.randint(_fewest(m), max(_fewest(m) + 6, min(50, round(80 / m))))
    b = pick(rng, max(4, round(5 * m)), max(5, round(12 * m)))
    d.param("face_width", b, "mm", "face width", f"{num(b)} mm face width")
    feature = _wheel(d, rng, "", m, z, "face_width", intent="transmits torque by meshing with its mating gear")
    d.say("Overall dimensions", f"{d.title}: {d.quote('module')}, {z} teeth, {num(b)} mm face width")
    bore = d.params[-1]["value"]
    d.say("Holes and ports", f"{num(bore)} mm bore")
    height = b
    root = m * (z - 2.5)
    if rng.random() < 0.4 and root - bore >= 12:
        hub_d = pick(rng, bore + 8, min(root - 2, bore + 30), 1)
        hub_l = pick(rng, 4, max(5, min(25, 2 * b)), 1)
        d.param("hub_diameter", hub_d, "mm", "hub diameter", f"{num(hub_d)} mm hub")
        d.param("hub_length", hub_l, "mm", "hub projection", f"{num(hub_l)} mm long")
        d.say("Features", f"a {num(hub_d)} mm hub on one side, projecting {num(hub_l)} mm long")
        feature |= {"hub_diameter": "hub_diameter", "hub_length": "hub_length"}
        height += hub_l
    d.features.append(feature)
    if bore > 6 and rng.random() < 0.4:
        d.say("Holes and ports", rng.choice(("a DIN 6885 keyway in the bore", "keyway in the bore to DIN 6885")))
        key = {"kind": "keyway", "id": "bore_key", "name": "Bore keyway", "of": "gear", "on": "bore"}
        d.features.append(key | {"intent": "locks the gear to the shaft with a parallel key"})
    d.need("extent", f"tip diameter {num(m * (z + 2))}", value=round(m * (z + 2), 3))
    d.need("extent", f"height {num(height)}", value=height)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _fewest(m: float) -> int:
    # enough teeth for a root diameter of 15 mm, so a 5 mm bore keeps the hole-edge rule
    return max(14, math.ceil(2.5 + 15 / m))


def _pair(rng: random.Random) -> Spec:
    d = Draft(rng.choice(PAIR_TITLES), "gear")
    m = _module(d, rng)
    z1 = rng.randint(_fewest(m), max(_fewest(m) + 6, 22))
    z2 = min(round(z1 * rng.choice((1.5, 2, 2.5, 3))), 60)
    b = pick(rng, max(4, round(5 * m)), max(5, round(10 * m)))
    a = m * (z1 + z2) / 2
    d.param("face_width", b, "mm", "face width of both gears", f"{num(b)} mm wide")
    pinion = _wheel(d, rng, "pinion", m, z1, "face_width", intent="driving gear on the input shaft")
    wheel = _wheel(d, rng, "wheel", m, z2, "face_width", intent="driven gear; reduces speed by the tooth ratio")
    bores = [p["value"] for p in d.params if p["name"].endswith("_bore")]
    d.say("Overall dimensions", f"{d.title}, {d.quote('module')}, both {num(b)} mm wide")
    d.say("Features", f"pinion with {z1} teeth and a {num(bores[0])} mm bore, wheel with {z2} teeth and a {num(bores[1])} mm bore")
    if rng.random() < 0.6:
        d.say("Features", rng.choice((f"meshing at {num(a)} mm centre distance", f"mounted {num(a)} mm apart, centre to centre")))
    else:
        d.say("Features", "meshing at the standard centre distance")
    if rng.random() < 0.3:
        backlash = rng.choice((0.05, 0.1, 0.15))
        d.param("backlash", backlash, "mm", "circular backlash of the pair", f"{num(backlash)} mm backlash")
        d.say("Features", f"{num(backlash)} mm backlash between the teeth")
        pinion["backlash"] = wheel["backlash"] = "backlash"
    joint: dict[str, Any] = {"id": "mesh", "parent": "pinion_axis", "child": "wheel_axis", "kind": "revolute"}
    if z2 % 2 == 0:
        # a wheel with an even tooth count faces the pinion's tooth with a tooth unless turned half a pitch
        joint["angle"] = "180 / wheel_teeth"
    d.parts = [
        {"id": "pinion", "name": "Pinion", "sketches": [], "features": [pinion]},
        {"id": "wheel", "name": "Wheel", "sketches": [], "features": [wheel]},
    ]
    origin = ["module * (pinion_teeth + wheel_teeth) / 2", 0, 0]
    connectors = [{"id": "pinion_axis", "part": "pinion", "origin": origin}, {"id": "wheel_axis", "part": "wheel"}]
    d.assembly = {"connectors": connectors, "joints": [joint]}
    d.need("hole_spacing", f"centre distance {num(a)}", value=a)
    d.need("extent", f"face width {num(b)}", value=b)
    return d.spec()
