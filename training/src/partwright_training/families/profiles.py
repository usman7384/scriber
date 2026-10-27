import random
from typing import Any

from partwright_training.fasteners import edge
from partwright_training.holes import bore, need_bores
from partwright_training.spec import Draft, Spec, count_word, finish, hole, num, pick

Point = tuple[Any, Any]
# B-type extrusion series used for training; 20 series is left out because the M1 set uses it
SERIES = {30: "M6", 40: "M8"}


def profile(rng: random.Random) -> Spec:
    return rng.choice((_l_plate, _t_plate, _u_plate, _gusset, _slotted))(rng)


def _outline(d: Draft, points: list[Point], thick: float, rounded: tuple[int, ...] = ()) -> None:
    d.param("thickness", thick, "mm", "plate thickness", f"{num(thick)} mm thick")
    entity: dict[str, Any] = {"kind": "polygon", "points": [list(p) for p in points]}
    if rounded:
        segments = [{"to": list(p), "fillet": "inside_radius" if i in rounded else 0} for i, p in enumerate(points[1:], 1)]
        entity = {"kind": "path", "start": list(points[0]), "segments": segments}
    d.sketches.append({"id": "outline", "plane": {"ref": "XY"}, "entities": [entity]})
    d.features.append({"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "outline", "distance": "thickness"})
    d.need("extent", f"thickness {num(thick)}", value=thick)


def _inside_radius(d: Draft, rng: random.Random, arm: float, corners: str) -> bool:
    if rng.random() < 0.6:
        return False
    r = pick(rng, 2, min(10, arm / 2))
    d.param("inside_radius", r, "mm", "inside corner radius", f"R{num(r)} {corners}")
    d.say("Features", f"R{num(r)} {corners}")
    return True


def _l_plate(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("L-shaped plate", "Corner plate", "Flat L plate", "Angle plate", "Corner joining plate")), "profile")
    arm = pick(rng, 20, 50, 5)
    length, height = pick(rng, arm + 40, 200, 5), pick(rng, arm + 30, 150, 5)
    thick = pick(rng, 3, 10)
    d.param("length", length, "mm", "overall length along X", f"outer size {num(length)} x {num(height)} mm")
    d.param("height", height, "mm", "overall size along Y", f"outer size {num(length)} x {num(height)} mm")
    d.param("arm_width", arm, "mm", "width of both arms", f"both arms {num(arm)} mm wide")
    sizes = f"outer size {num(length)} x {num(height)} mm, both arms {num(arm)} mm wide"
    d.say("Overall dimensions", f"{d.title}, {sizes}, {num(thick)} mm thick")
    corner = (3,) if _inside_radius(d, rng, arm, "inside corner") else ()
    inner = ("arm_width", "arm_width")
    points: list[Point] = [(0, 0), ("length", 0), ("length", "arm_width"), inner, ("arm_width", "height"), (0, "height")]
    _outline(d, points, thick, corner)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"height {num(height)}", value=height)
    size = rng.choice([s for s in ("M4", "M5", "M6", "M8") if 2 * edge(s) <= arm])
    free = length - arm - 2 * edge(size)
    n = rng.randint(2, 4)
    pitch = pick(rng, 15, max(15, min(60, free / (n - 1))), 5)
    if pitch * (n - 1) > free:
        n, pitch = 2, pick(rng, 10, max(10, free), 1)
    if pitch > free:
        finish(d, rng, "milling_3axis")
        return d.spec()
    b = bore(d, rng, size, "simple")
    word = count_word(rng, n)
    d.param("hole_pitch", pitch, "mm", "hole centre distance", f"{num(pitch)} mm apart")
    where = f"along the middle of the {num(length)} mm arm, centred in its free length"
    d.say("Holes and ports", f"{b.many(word)} holes {num(pitch)} mm apart {where}")
    start = (f"(arm_width + length) / 2 - {n - 1} * hole_pitch / 2", "arm_width / 2")
    d.features.append(hole("arm_hole", "Arm hole", "plate.top", [start], **b.spec))
    d.features.append(
        {"kind": "pattern", "id": "arm_row", "name": "Arm holes", "features": ["arm_hole"], "type": "linear", "count": n}
        | {"direction": "x", "spacing": "hole_pitch"}
    )
    need_bores(d, b, n)
    d.need("hole_spacing", f"{num(pitch)} mm apart", value=pitch)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _t_plate(rng: random.Random) -> Spec:
    series = rng.choice(list(SERIES))
    size = SERIES[series]
    bars, stems = rng.randint(3, 5), rng.randint(1, 3)
    if bars % 2 == 0:
        bars += 1
    d = Draft(rng.choice(("T-shaped joining plate", "T plate", "T joining plate", "Tee connector plate")), "profile")
    thick = pick(rng, 4, 8)
    length, height = bars * series, (stems + 1) * series
    d.param("slot_pitch", series, "mm", "extrusion slot centres", f"{series} mm slot centres")
    d.param("bar_slots", bars, "", "slot positions across the bar", f"{bars} slot positions across the bar")
    d.param("stem_slots", stems, "", "slot positions down the stem", f"{stems} more down the stem")
    d.say("Overall dimensions", f"{d.title} for {series}{series} aluminium extrusion, {num(thick)} mm thick")
    d.say("Overall dimensions", f"{bars} slot positions across the bar and {stems} more down the stem, on the {series} mm slot centres")
    half = "bar_slots * slot_pitch / 2"
    points: list[Point] = [
        (f"-{half}", 0),
        (half, 0),
        (half, "slot_pitch"),
        ("slot_pitch / 2", "slot_pitch"),
        ("slot_pitch / 2", "(stem_slots + 1) * slot_pitch"),
        ("-slot_pitch / 2", "(stem_slots + 1) * slot_pitch"),
        ("-slot_pitch / 2", "slot_pitch"),
        (f"-{half}", "slot_pitch"),
    ]
    _outline(d, points, thick)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"height {num(height)}", value=height)
    b = bore(d, rng, size, "simple")
    total = bars + stems
    d.say("Holes and ports", f"{b.many(count_word(rng, total))} holes, one on each slot centre")
    d.features.append(hole("bar_hole", "Bar hole", "plate.top", [("-(bar_slots - 1) * slot_pitch / 2", "slot_pitch / 2")], **b.spec))
    d.features.append(
        {"kind": "pattern", "id": "bar_row", "name": "Bar holes", "features": ["bar_hole"], "type": "linear", "count": "bar_slots"}
        | {"direction": "x", "spacing": "slot_pitch"}
    )
    d.features.append(hole("stem_hole", "Stem hole", "plate.top", [(0, "slot_pitch * 1.5")], **b.spec))
    if stems > 1:
        d.features.append(
            {"kind": "pattern", "id": "stem_row", "name": "Stem holes", "features": ["stem_hole"], "type": "linear", "count": "stem_slots"}
            | {"direction": "y", "spacing": "slot_pitch"}
        )
    need_bores(d, b, total)
    d.need("hole_spacing", f"{series} mm slot centres", value=series)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _u_plate(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("U-shaped plate", "Fork plate", "Flat U bracket", "Clevis plate")), "profile")
    arm = pick(rng, 15, 40, 5)
    gap = pick(rng, 20, 80, 5)
    width, depth = gap + 2 * arm, pick(rng, arm + 30, 150, 5)
    thick = pick(rng, 3, 12)
    d.param("width", width, "mm", "overall width", f"{num(width)} mm wide overall")
    d.param("depth", depth, "mm", "overall depth", f"{num(depth)} mm deep")
    d.param("arm_width", arm, "mm", "arm width", f"{num(arm)} mm wide arms")
    extent = f"{num(width)} mm wide overall and {num(depth)} mm deep, {num(arm)} mm wide arms and base"
    d.say("Overall dimensions", f"{d.title}, {extent}, {num(thick)} mm thick")
    inner = "width / 2 - arm_width"
    points: list[Point] = [
        ("-width / 2", 0),
        ("width / 2", 0),
        ("width / 2", "depth"),
        (inner, "depth"),
        (inner, "arm_width"),
        (f"-({inner})", "arm_width"),
        (f"-({inner})", "depth"),
        ("-width / 2", "depth"),
    ]
    _outline(d, points, thick, (4, 5) if _inside_radius(d, rng, min(arm, gap), "inside corners") else ())
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"depth {num(depth)}", value=depth)
    sizes = [s for s in ("M4", "M5", "M6", "M8", "M10") if 2 * edge(s) <= arm and edge(s) <= depth - arm - 2]
    if sizes:
        size = rng.choice(sizes)
        b = bore(d, rng, size, "simple")
        reach = pick(rng, edge(size), depth - edge(size))
        d.param("hole_from_end", reach, "mm", "arm hole centre from the open end", f"{num(reach)} mm from the open end")
        d.say("Holes and ports", f"one {b.words} hole in each arm on its centre line, {num(reach)} mm from the open end")
        d.features.append(hole("arm_holes", "Arm holes", "plate.top", [(f"-({inner}) - arm_width / 2", "depth - hole_from_end")], **b.spec))
        d.features.append(
            {"kind": "pattern", "id": "arm_mirror", "name": "Other arm", "features": ["arm_holes"], "type": "mirror", "mirror_plane": "YZ"}
        )
        need_bores(d, b, 2)
        d.need("hole_spacing", f"arm holes {num(width - arm)} apart", value=width - arm)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _gusset(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Gusset plate", "Triangular gusset", "Corner gusset", "Stiffener plate")), "profile")
    base, height, thick = pick(rng, 40, 160, 5), pick(rng, 40, 160, 5), pick(rng, 3, 10)
    d.param("base", base, "mm", "length along the bottom", f"{num(base)} mm along the bottom")
    d.param("height", height, "mm", "height", f"{num(height)} mm high")
    sizes = f"{num(base)} mm along the bottom and {num(height)} mm high"
    d.say("Overall dimensions", f"right-angled {d.title.lower()}, {sizes}, {num(thick)} mm thick")
    _outline(d, [(0, 0), ("base", 0), (0, "height")], thick)
    d.need("extent", f"base {num(base)}", value=base)
    d.need("extent", f"height {num(height)}", value=height)
    size = rng.choice(("M4", "M5", "M6", "M8"))
    inset = pick(rng, max(10, edge(size)), max(10, min(base, height) / 4))
    # the hole must also clear the sloped edge: its distance is (1 - x/a - y/b) / |n| for a point (x, x)
    slope_gap = (1 - inset / base - inset / height) / ((1 / base**2 + 1 / height**2) ** 0.5)
    if slope_gap < edge(size) + 1:
        finish(d, rng, "milling_3axis")
        return d.spec()
    b = bore(d, rng, size, "simple")
    d.param("hole_inset", inset, "mm", "hole centre from both straight edges", f"{num(inset)} mm from both straight edges")
    d.say("Holes and ports", f"one {b.words} hole {num(inset)} mm from both straight edges")
    d.features.append(hole("corner_hole", "Corner hole", "plate.top", [("hole_inset", "hole_inset")], **b.spec))
    need_bores(d, b, 1)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _slotted(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Adjustment plate", "Slotted plate", "Tensioner plate", "Slotted mounting plate")), "profile")
    length, width, thick = pick(rng, 80, 200, 5), pick(rng, 30, 80, 5), pick(rng, 3, 10)
    slot_w = rng.choice((5.5, 6.5, 8.5, 10.5))
    slot_l = pick(rng, slot_w + 8, min(60, length / 3), 1)
    gap = pick(rng, slot_l + 10, max(slot_l + 10, length - slot_l - 20), 5)
    if gap + slot_l > length - 16 or width < 2 * slot_w + 10:
        gap = 0.0
    d.param("length", length, "mm", "plate length", f"{num(length)} x {num(width)} x {num(thick)} mm")
    d.param("width", width, "mm", "plate width", f"{num(length)} x {num(width)} x {num(thick)} mm")
    d.param("thickness", thick, "mm", "plate thickness", f"{num(length)} x {num(width)} x {num(thick)} mm")
    d.say("Overall dimensions", f"{d.title} {num(length)} x {num(width)} x {num(thick)} mm")
    entities: list[dict[str, Any]] = [{"kind": "rect", "width": "length", "height": "width"}]
    d.param("slot_width", slot_w, "mm", "slot width", f"{num(slot_w)} mm wide")
    d.param("slot_length", slot_l, "mm", "slot overall length", f"{num(slot_l)} mm long")
    if gap:
        d.param("slot_spacing", gap, "mm", "slot centre distance", f"slot centres {num(gap)} mm apart")
        d.say("Features", f"two {num(slot_w)} mm wide, {num(slot_l)} mm long slots along the length, slot centres {num(gap)} mm apart")
        centres: list[Point] = [("-slot_spacing / 2", 0), ("slot_spacing / 2", 0)]
    else:
        d.say("Features", f"one {num(slot_w)} mm wide, {num(slot_l)} mm long slot along the length in the middle")
        centres = [(0, 0)]
    entities += [{"kind": "slot", "center": list(c), "length": "slot_length", "width": "slot_width", "subtract": True} for c in centres]
    d.sketches.append({"id": "outline", "plane": {"ref": "XY"}, "entities": entities})
    d.features.append({"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "outline", "distance": "thickness"})
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"thickness {num(thick)}", value=thick)
    finish(d, rng, "milling_3axis")
    return d.spec()
