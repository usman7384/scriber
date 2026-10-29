import math
import random
from typing import Any

from partwright_training.fasteners import edge, head
from partwright_training.holes import bore, need_bores
from partwright_training.spec import Draft, Spec, circle_sketch, count_word, finish, hole, num, pick

TITLES = ("Flange coupling", "Rigid shaft coupling", "Bolted flange coupling", "Split flange coupling")


def coupling(rng: random.Random) -> Spec:
    d = Draft(rng.choice(TITLES), "assembly")
    shaft = pick(rng, 12, 40, 1)
    hub = pick(rng, max(shaft + 16, 3 * shaft), 3 * shaft + 10, 2)
    size = rng.choice(("M5", "M6", "M8", "M10"))
    pcd = pick(rng, math.ceil(hub + head(size) + 4), hub + head(size) + 20, 1)
    dia = pick(rng, math.ceil(pcd + 2 * edge(size)), pcd + 2 * edge(size) + 20, 2)
    t, hub_l = pick(rng, 8, 20), pick(rng, 15, 50, 1)
    n = rng.choice((3, 4, 6))
    d.param("shaft_diameter", shaft, "mm", "bore for the shafts", f"two {num(shaft)} mm shafts")
    d.param("flange_diameter", dia, "mm", "flange outside diameter", f"flange of {num(dia)} mm diameter")
    d.param("flange_thickness", t, "mm", "flange thickness", f"{num(t)} mm thickness")
    d.param("hub_diameter", hub, "mm", "hub outside diameter", f"{num(hub)} mm hub")
    d.param("hub_length", hub_l, "mm", "hub length beyond the flange", f"extending {num(hub_l)} mm")
    d.param("bolt_count", n, "", "bolts through the flanges", f"{count_word(rng, n)} bolts")
    d.param("bolt_circle", pcd, "mm", "bolt circle diameter", f"pitch circle {num(pcd)} mm")
    d.say(
        "Overall dimensions", f"{d.title} joining two {num(shaft)} mm shafts, made as a matched pair of halves whose flanges bolt together"
    )
    d.say(
        "Features",
        f"per half a flange of {num(dia)} mm diameter and {num(t)} mm thickness, plus a {num(hub)} mm hub extending {num(hub_l)} mm",
    )
    d.say("Holes and ports", "keyed bores to DIN 6885")
    b = bore(d, rng, size, "simple", "bolt_hole_diameter")
    d.say("Holes and ports", f"{d.quote('bolt_count')} pass through {b.words} holes in both flanges, pitch circle {num(pcd)} mm")
    d.take(shaft, shaft)
    d.parts = [_half("half_a", "Half A", b.spec), _half("half_b", "Half B", b.spec)]
    connectors = [
        {"id": "face_a", "part": "half_a", "z": "-z"},
        {"id": "face_b", "part": "half_b"},
    ]
    d.assembly = {"connectors": connectors, "joints": [{"id": "bolted_faces", "parent": "face_a", "child": "face_b"}]}
    need_bores(d, b, 2 * n, "bolt holes")
    if n % 2 == 0:
        d.need("hole_spacing", f"bolt circle {num(pcd)}", value=pcd, diameter_min=b.lo, diameter_max=b.hi)
    d.need("extent", f"flange {num(dia)}", value=dia)
    d.need("extent", f"length {num(2 * (t + hub_l))}", value=2 * (t + hub_l))
    finish(d, rng, "turning")
    for part in d.parts:
        if d.material:
            part["material"] = d.material
    return d.spec()


def _half(pid: str, name: str, bolt: dict[str, Any]) -> dict[str, Any]:
    at = {"kind": "polar", "count": "bolt_count", "diameter": "bolt_circle"}
    features = [
        {"kind": "extrude", "id": "flange", "name": "Flange", "sketch": "flange", "distance": "flange_thickness", "intent": "bolting face"},
        {
            "kind": "extrude",
            "id": "hub",
            "name": "Hub",
            "sketch": "hub",
            "distance": "hub_length",
            "intent": "grips the shaft over its length",
        },
        hole("bore", "Bore", "hub.end", [(0, 0)], diameter="shaft_diameter", intent="fits the shaft"),
        {"kind": "keyway", "id": "key", "name": "Keyway", "of": "bore", "on": "bore", "intent": "drives the shaft through a parallel key"},
        {
            "kind": "hole",
            "id": "bolts",
            "name": "Bolt holes",
            "plane": {"ref": "flange.start"},
            "at": at,
            **bolt,
            "intent": "bolt the halves together",
        },
    ]
    sketches = [circle_sketch("flange", "flange_diameter", "XY"), circle_sketch("hub", "hub_diameter", "flange.end")]
    return {"id": pid, "name": name, "sketches": sketches, "features": features}
