import math
import random
from typing import Any

from scriber_training.families.couplings import coupling
from scriber_training.fasteners import clearance, edge, head, nominal, tap_drill, thread
from scriber_training.spec import Draft, Spec, circle_sketch, finish, hole, num, pick, rect_sketch

CORNERS = ((-1, -1), (1, -1), (1, 1), (-1, 1))


def assembly(rng: random.Random) -> Spec:
    return rng.choice((_standoff_stack, _clamp, _servo_mount, _hinge, coupling))(rng)


def _plate(pid: str, name: str, length: str, width: str, thick: str, holes: dict[str, Any], intent: str) -> dict[str, Any]:
    body = {"kind": "extrude", "id": "plate", "name": name, "sketch": "outline", "distance": thick, "intent": intent}
    return {"id": pid, "name": name, "sketches": [rect_sketch("outline", length, width)], "features": [body, holes]}


def _grid(size: str, intent: str, **kind: Any) -> dict[str, Any]:
    at = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "hole_spacing_x", "spacing_y": "hole_spacing_y"}
    return {"kind": "hole", "id": "holes", "name": f"{size} holes", "plane": {"ref": "plate.end"}, "at": at, "fastener": size, **kind}


def _standoff_stack(rng: random.Random) -> Spec:
    d = Draft(
        rng.choice(("Board mount", "PCB standoff stack", "Two-plate stack", "Electronics mounting stack", "Sandwich mount")), "assembly"
    )
    size = rng.choice(("M3", "M4"))
    sx, sy = pick(rng, 40, 120, 5), pick(rng, 30, 90, 5)
    margin = edge(size) + rng.choice((0, 2, 5))
    base = (sx + 2 * margin + pick(rng, 0, 30, 5), sy + 2 * margin + pick(rng, 0, 20, 5), pick(rng, 3, 8))
    top = (sx + 2 * margin, sy + 2 * margin, pick(rng, 1.5, 3, 0.5))
    # the default hole-edge rule wants the standoff wall around its tap drill to be 1.5 x that drill
    od, tall = rng.choice((8.0, 9.0)) if size == "M3" else rng.choice((10.0, 11.0)), pick(rng, 8, 40)
    d.param("base_length", base[0], "mm", "base plate length", f"base plate {num(base[0])} x {num(base[1])} x {num(base[2])} mm")
    d.param("base_width", base[1], "mm", "base plate width", f"base plate {num(base[0])} x {num(base[1])} x {num(base[2])} mm")
    d.param("base_thickness", base[2], "mm", "base plate thickness", f"base plate {num(base[0])} x {num(base[1])} x {num(base[2])} mm")
    d.param("top_length", top[0], "mm", "top plate length", f"top plate {num(top[0])} x {num(top[1])} x {num(top[2])} mm")
    d.param("top_width", top[1], "mm", "top plate width", f"top plate {num(top[0])} x {num(top[1])} x {num(top[2])} mm")
    d.param("top_thickness", top[2], "mm", "top plate thickness", f"top plate {num(top[0])} x {num(top[1])} x {num(top[2])} mm")
    d.param("hole_spacing_x", sx, "mm", "hole centres along X", f"{num(sx)} x {num(sy)} mm")
    d.param("hole_spacing_y", sy, "mm", "hole centres along Y", f"{num(sx)} x {num(sy)} mm")
    d.param("standoff_diameter", od, "mm", "standoff diameter", f"{num(od)} mm round standoffs")
    d.param("standoff_height", tall, "mm", "standoff length", f"{num(tall)} mm long")
    d.say("Overall dimensions", f"{d.title}: a base plate {num(base[0])} x {num(base[1])} x {num(base[2])} mm")
    d.say("Overall dimensions", f"a top plate {num(top[0])} x {num(top[1])} x {num(top[2])} mm held above it")
    d.say("Features", f"four {num(od)} mm round standoffs {num(tall)} mm long, tapped {size} through")
    d.say("Holes and ports", f"{size} clearance holes in both plates on {num(sx)} x {num(sy)} mm, one above each standoff")
    d.parts = [
        _plate(
            "base",
            "Base plate",
            "base_length",
            "base_width",
            "base_thickness",
            _grid(size, "screws into the standoffs"),
            "carries the stack",
        ),
        _plate(
            "top",
            "Top plate",
            "top_length",
            "top_width",
            "top_thickness",
            _grid(size, "screws into the standoffs"),
            "the board or panel held above the base",
        ),
    ]
    tapped = {"type": "tapped", "fastener": size, "thread": thread(size), "intent": "takes the plate screws from both ends"}
    connectors: list[dict[str, Any]] = [{"id": "top_seat", "part": "top", "origin": ["-hole_spacing_x / 2", "-hole_spacing_y / 2", 0]}]
    joints = []
    for i, (cx, cy) in enumerate(CORNERS, 1):
        post = {
            "kind": "extrude",
            "id": "post",
            "name": "Standoff",
            "sketch": "round",
            "distance": "standoff_height",
            "intent": "spaces the plates",
        }
        bore = hole("thread", "Tapped hole", "post.end", [(0, 0)], **tapped)
        d.parts.insert(
            i,
            {
                "id": f"standoff_{i}",
                "name": f"Standoff {i}",
                "sketches": [circle_sketch("round", "standoff_diameter", "XY")],
                "features": [post, bore],
            },
        )
        x, y = f"{'-' if cx < 0 else ''}hole_spacing_x / 2", f"{'-' if cy < 0 else ''}hole_spacing_y / 2"
        connectors += [
            {"id": f"seat_{i}", "part": "base", "origin": [x, y, "base_thickness"]},
            {"id": f"foot_{i}", "part": f"standoff_{i}"},
        ]
        joints.append({"id": f"standoff_{i}_on_base", "parent": f"seat_{i}", "child": f"foot_{i}"})
    connectors.append({"id": "head_1", "part": "standoff_1", "origin": [0, 0, "standoff_height"]})
    joints.append({"id": "top_on_standoff_1", "parent": "head_1", "child": "top_seat"})
    d.assembly = {"connectors": connectors, "joints": joints}
    lo, hi = clearance(size)
    tap = tap_drill(size)
    d.need("holes", f"eight {size} clearance holes", count=8, diameter_min=lo, diameter_max=hi)
    d.need("holes", f"four {size} tapped standoffs", count=4, diameter_min=tap - 0.1, diameter_max=tap + 0.1)
    d.need("hole_spacing", f"{num(sx)} apart", value=sx, diameter_min=lo, diameter_max=hi)
    d.need("extent", f"length {num(base[0])}", value=base[0])
    d.need("extent", f"height {num(base[2] + tall + top[2])}", value=base[2] + tall + top[2])
    finish(d, rng, "milling_3axis")
    return d.spec()


def _clamp(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Shaft clamp", "Split clamp block", "Pipe clamp", "Rod clamp", "Split bearing clamp")), "assembly")
    dia = pick(rng, 8, 40, 1)
    size = rng.choice(("M4", "M5", "M6", "M8"))
    spacing = pick(rng, dia + head(size) + 4, dia + head(size) + 20, 1)
    length = pick(rng, spacing + 2 * edge(size), spacing + 2 * edge(size) + 20, 1)
    width = pick(rng, max(12, 2 * edge(size)), 40, 1)
    low = pick(rng, dia / 2 + 6, dia / 2 + 20, 1)
    cap = pick(rng, max(dia / 2 + 4, 1.5 * nominal(size) + 4), dia / 2 + 15, 1)
    deep = pick(rng, 1.5 * nominal(size) + 2, max(1.5 * nominal(size) + 2, low - 3), 1)
    d.param("bore_diameter", dia, "mm", "clamped diameter", f"{num(dia)} mm")
    d.param("length", length, "mm", "block length", f"{num(length)} mm long")
    d.param("width", width, "mm", "block width along the bore", f"{num(width)} mm wide")
    d.param("base_height", low, "mm", "lower block height", f"lower block {num(low)} mm high")
    d.param("cap_height", cap, "mm", "cap height", f"cap {num(cap)} mm high")
    d.param("screw_spacing", spacing, "mm", "clamp screw centres", f"{num(spacing)} mm apart")
    d.param("thread_depth", deep, "mm", "tapped hole depth", f"{num(deep)} mm deep")
    d.say("Overall dimensions", f"{d.title} for a {num(dia)} mm bar, {num(length)} mm long and {num(width)} mm wide")
    d.say("Features", f"split on the bore centre line: lower block {num(low)} mm high, cap {num(cap)} mm high")
    d.say("Holes and ports", f"two {size} screws {num(spacing)} mm apart through the cap into tapped holes {num(deep)} mm deep")
    pins = [("-screw_spacing / 2", 0), ("screw_spacing / 2", 0)]
    half_bore = {"kind": "extrude", "id": "bore", "name": "Half bore", "sketch": "bore", "mode": "cut", "extent": "symmetric"}
    half_bore |= {"distance": "2 * width", "intent": "half of the clamping bore"}
    lower = [
        {"kind": "extrude", "id": "block", "name": "Lower block", "sketch": "outline", "distance": "base_height", "intent": "fixed half"},
        half_bore,
        hole("tapped", f"{size} tapped holes", "block.top", pins, type="tapped", fastener=size, thread=thread(size), depth="thread_depth")
        | {"intent": "take the clamp screws"},
    ]
    upper = [
        {"kind": "extrude", "id": "cap", "name": "Cap", "sketch": "outline", "distance": "cap_height", "intent": "removable half"},
        half_bore,
        hole("screws", f"{size} clearance holes", "cap.top", pins, fastener=size, intent="pass the clamp screws"),
    ]
    d.parts = [
        {
            "id": "lower",
            "name": "Lower block",
            "sketches": [rect_sketch("outline", "length", "width"), _bore((0, "base_height"))],
            "features": lower,
        },
        {"id": "cap", "name": "Cap", "sketches": [rect_sketch("outline", "length", "width"), _bore((0, 0))], "features": upper},
    ]
    connectors = [{"id": "split_face", "part": "lower", "origin": [0, 0, "base_height"]}, {"id": "cap_face", "part": "cap"}]
    d.assembly = {"connectors": connectors, "joints": [{"id": "cap_on_block", "parent": "split_face", "child": "cap_face"}]}
    lo, hi = clearance(size)
    tap = tap_drill(size)
    d.need("holes", f"two {size} clearance holes", count=2, diameter_min=lo, diameter_max=hi)
    d.need("holes", f"two {size} tapped holes", count=2, diameter_min=tap - 0.1, diameter_max=tap + 0.1)
    d.need("hole_spacing", f"{num(spacing)} apart", value=spacing)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"height {num(low + cap)}", value=low + cap)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _bore(center: tuple[Any, Any]) -> dict[str, Any]:
    return {"id": "bore", "plane": {"ref": "XZ"}, "entities": [{"kind": "circle", "center": list(center), "diameter": "bore_diameter"}]}


def _servo_mount(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Servo mount", "Servo bracket", "Servo mounting plate", "Actuator mount")), "assembly")
    bx, by, bh = pick(rng, 22, 42, 0.5), pick(rng, 16, 22, 0.5), pick(rng, 22, 40, 0.5)
    hole_d, gap = rng.choice((2.2, 2.7, 3.2)), rng.choice((0.5, 1.0))
    # ear holes keep 1.5 x their diameter to the ear's end and to the plate's cut-out
    ear = pick(rng, 3 * hole_d + 2 * gap + 0.5, 3 * hole_d + 2 * gap + 3, 0.5)
    ear_t, ear_z = pick(rng, 2, 3, 0.5), pick(rng, bh * 0.5, bh * 0.75, 0.5)
    ex, ey = bx + ear, round(by - 3 * hole_d, 1)
    t = pick(rng, 3, 6)
    margin = max(10, 2 * edge("M4"))
    length, width = (
        pick(rng, bx + 2 * ear + 2 * margin, bx + 2 * ear + 2 * margin + 30, 5),
        pick(rng, by + 2 * margin, by + 2 * margin + 30, 5),
    )
    d.param("servo_length", bx, "mm", "servo body length", f"{num(bx)} x {num(by)} mm body")
    d.param("servo_width", by, "mm", "servo body width", f"{num(bx)} x {num(by)} mm body")
    d.param("servo_height", bh, "mm", "servo body height", f"{num(bh)} mm tall")
    d.param("ear_length", ear, "mm", "ear reach beyond the body", f"ears reaching {num(ear)} mm past each end")
    d.param("ear_thickness", ear_t, "mm", "ear thickness", f"{num(ear_t)} mm thick")
    d.param("ear_height", ear_z, "mm", "ear underside above the servo bottom", f"{num(ear_z)} mm above its bottom")
    d.param("ear_hole_diameter", hole_d, "mm", "ear screw holes", f"{num(hole_d)} mm holes")
    d.param("ear_hole_spacing_x", ex, "mm", "ear hole centres along the body", f"on {num(ex)} x {num(ey)} mm")
    d.param("ear_hole_spacing_y", ey, "mm", "ear hole centres across the body", f"on {num(ex)} x {num(ey)} mm")
    d.param("plate_length", length, "mm", "plate length", f"{num(length)} x {num(width)} x {num(t)} mm plate")
    d.param("plate_width", width, "mm", "plate width", f"{num(length)} x {num(width)} x {num(t)} mm plate")
    d.param("thickness", t, "mm", "plate thickness", f"{num(length)} x {num(width)} x {num(t)} mm plate")
    d.param("cutout_clearance", gap, "mm", "clearance around the servo body", f"{num(gap)} mm clearance all round")
    d.say("Overall dimensions", f"{d.title}: a {num(length)} x {num(width)} x {num(t)} mm plate holding a hobby servo")
    d.say("Features", f"servo: {num(bx)} x {num(by)} mm body, {num(bh)} mm tall, ears reaching {num(ear)} mm past each end")
    d.say("Features", f"the ears are {num(ear_t)} mm thick, their underside {num(ear_z)} mm above its bottom")
    d.say("Holes and ports", f"{num(hole_d)} mm holes in the ears on {num(ex)} x {num(ey)} mm, matching holes in the plate")
    d.say("Features", f"the body drops through a cut-out in the plate with {num(gap)} mm clearance all round")
    ears = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "ear_hole_spacing_x", "spacing_y": "ear_hole_spacing_y"}
    cut = rect_sketch("cutout", "servo_length + 2 * cutout_clearance", "servo_width + 2 * cutout_clearance", plane="plate.end")
    plate = [
        {"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "outline", "distance": "thickness", "intent": "carries the servo"},
        {"kind": "extrude", "id": "cutout", "name": "Servo cut-out", "sketch": "cutout", "mode": "cut", "extent": "through_all"}
        | {"intent": "lets the servo body pass through"},
        {"kind": "hole", "id": "ear_holes", "name": "Ear holes", "plane": {"ref": "plate.end"}, "at": ears, "diameter": "ear_hole_diameter"}
        | {"intent": "screws through the servo ears"},
    ]
    ear_plane = {"ref": "XY", "offset": "ear_height"}
    servo = [
        {
            "kind": "extrude",
            "id": "body",
            "name": "Body",
            "sketch": "body",
            "distance": "servo_height",
            "intent": "stand-in for the servo case",
        },
        {"kind": "extrude", "id": "ears", "name": "Ears", "sketch": "ears", "distance": "ear_thickness", "intent": "mounting flange"},
        {"kind": "hole", "id": "ear_holes", "name": "Ear holes", "plane": {"ref": "ears.end"}, "at": ears, "diameter": "ear_hole_diameter"}
        | {"intent": "mounting screw holes"},
    ]
    d.parts = [
        {"id": "plate", "name": "Plate", "sketches": [rect_sketch("outline", "plate_length", "plate_width"), cut], "features": plate},
        {
            "id": "servo",
            "name": "Servo",
            "sketches": [
                rect_sketch("body", "servo_length", "servo_width"),
                {
                    "id": "ears",
                    "plane": ear_plane,
                    "entities": [{"kind": "rect", "width": "servo_length + 2 * ear_length", "height": "servo_width"}],
                },
            ],
            "features": servo,
        },
    ]
    connectors = [
        {"id": "plate_top", "part": "plate", "origin": [0, 0, "thickness"]},
        {"id": "ear_seat", "part": "servo", "origin": [0, 0, "ear_height"]},
    ]
    d.assembly = {"connectors": connectors, "joints": [{"id": "servo_on_plate", "parent": "plate_top", "child": "ear_seat"}]}
    d.need("holes", f"eight {num(hole_d)} holes", count=8, diameter_min=hole_d - 0.1, diameter_max=hole_d + 0.1)
    d.need("hole_spacing", f"{num(ex)} apart", value=ex, diameter_min=hole_d - 0.1, diameter_max=hole_d + 0.1)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"height {num(bh)}", value=bh)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _hinge(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Butt hinge", "Hinge", "Door hinge", "Leaf hinge", "Pin hinge")), "assembly")
    size = rng.choice(("M3", "M4"))
    lo, hi = clearance(size)
    pin = rng.choice([v / 2 for v in range(6, 13) if not lo - 0.2 <= v / 2 <= hi + 0.2])
    # the knuckle keeps 1.5 x the pin diameter round the pin, as the default hole-edge rule asks
    knuckle = pick(rng, 3 * pin, 3 * pin + 4, 1)
    length, t = pick(rng, 45, 120, 5), pick(rng, 2, 4, 0.5)
    leaf = pick(rng, math.ceil(knuckle / 2 + 3 * hi + 2), knuckle / 2 + 3 * hi + 20, 1)
    spacing = pick(rng, 15, length - 2 * edge(size) - 2.5, 5)
    d.param("hinge_length", length, "mm", "length along the pin", f"{num(length)} mm long")
    d.param("leaf_width", leaf, "mm", "leaf width from the pin axis", f"leaves {num(leaf)} mm wide")
    d.param("leaf_thickness", t, "mm", "leaf thickness", f"{num(t)} mm thick")
    d.param("pin_diameter", pin, "mm", "pin hole diameter", f"{num(pin)} mm pin")
    d.param("knuckle_diameter", knuckle, "mm", "knuckle outside diameter", f"{num(knuckle)} mm knuckles")
    d.param("screw_spacing", spacing, "mm", "screw hole centres along each leaf", f"{num(spacing)} mm apart")
    d.say(
        "Overall dimensions", f"{d.title} {num(length)} mm long, leaves {num(leaf)} mm wide from the pin axis, {num(t)} mm thick, open flat"
    )
    d.say(
        "Features",
        f"three {num(knuckle)} mm knuckles of equal length on a {num(pin)} mm pin; the outer two on one leaf, the middle one on the other",
    )
    d.say("Holes and ports", f"two {size} clearance holes in each leaf, {num(spacing)} mm apart, midway across the leaf")
    parts = []
    for pid, sign, starts in (("leaf_a", "-", ("-hinge_length / 2", "hinge_length / 6")), ("leaf_b", "", ("-hinge_length / 6",))):
        mid = f"{sign}(leaf_width + knuckle_diameter / 2) / 2"
        plate = rect_sketch("leaf", "hinge_length", "leaf_width - knuckle_diameter / 2", center=(0, mid))
        plate["plane"] = {"ref": "XY", "offset": "-leaf_thickness / 2"}
        sketches = [plate]
        features: list[dict[str, Any]] = [
            {
                "kind": "extrude",
                "id": "leaf",
                "name": "Leaf",
                "sketch": "leaf",
                "distance": "leaf_thickness",
                "intent": "screws to the door or frame",
            }
        ]
        for k, x0 in enumerate(starts, 1):
            band = {
                "kind": "rect",
                "width": "knuckle_diameter / 2",
                "height": "leaf_thickness",
                "center": [f"{sign}knuckle_diameter / 4", 0],
            }
            ring = {"kind": "circle", "diameter": "knuckle_diameter"}
            sketches.append({"id": f"knuckle_{k}", "plane": {"ref": "YZ", "offset": x0}, "entities": [ring, band]})
            knuckle_f = {
                "kind": "extrude",
                "id": f"knuckle_{k}",
                "name": f"Knuckle {k}",
                "sketch": f"knuckle_{k}",
                "distance": "hinge_length / 3",
            }
            features.append(knuckle_f | {"intent": "wraps the pin"})
        pin_hole = hole("pin_hole", "Pin hole", "YZ", [(0, 0)], diameter="pin_diameter", intent="the hinge axis")
        features.append(pin_hole | {"plane": {"ref": "YZ", "offset": "-hinge_length / 2"}})
        screws = [("-screw_spacing / 2", mid), ("screw_spacing / 2", mid)]
        features.append(hole("screw_holes", f"{size} screw holes", "leaf.end", screws, fastener=size, intent="fix the leaf"))
        parts.append({"id": pid, "name": f"Leaf {pid[-1].upper()}", "sketches": sketches, "features": features})
    d.parts = parts
    axis = {"z": "+x", "x": "+y"}
    connectors = [{"id": "axis_a", "part": "leaf_a", **axis}, {"id": "axis_b", "part": "leaf_b", **axis}]
    d.assembly = {"connectors": connectors, "joints": [{"id": "hinge", "parent": "axis_a", "child": "axis_b", "kind": "revolute"}]}
    d.need("min_holes", f"pin hole {num(pin)}", count=2, diameter_min=pin - 0.1, diameter_max=pin + 0.1)
    d.need("holes", f"four {size} screw holes", count=4, diameter_min=lo, diameter_max=hi)
    d.need("hole_spacing", f"{num(spacing)} apart", value=spacing, diameter_min=lo, diameter_max=hi)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(2 * leaf)}", value=2 * leaf)
    finish(d, rng, "milling_3axis")
    return d.spec()
