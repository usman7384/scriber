import random
from typing import Any

from partwright_training.fasteners import counterbore_depth, edge, head
from partwright_training.holes import bore, corner_grid, need_bores
from partwright_training.spec import Draft, Spec, circle_sketch, count_word, finish, hole, num, pick, rect_sketch

Point = tuple[Any, Any]
SIZES = ("M4", "M5", "M6", "M8")


def support(rng: random.Random) -> Spec:
    return rng.choice((_gusseted, _gusseted, _z_bracket, _hat, _clevis, _pedestal, _lug))(rng)


def _profile(d: Draft, points: list[Point], width: str, intent: str) -> None:
    d.sketches.append({"id": "profile", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": [list(p) for p in points]}]})
    body = {"kind": "extrude", "id": "body", "name": "Profile", "sketch": "profile", "extent": "symmetric", "distance": width}
    d.features.append(body | {"intent": intent})


def _gusseted(rng: random.Random) -> Spec:
    d = Draft(
        rng.choice(("Gusseted angle bracket", "Reinforced angle bracket", "Braced angle", "Stiffened L bracket", "Angle support")),
        "support",
    )
    t, a, b, w = pick(rng, 3, 8), pick(rng, 50, 120, 5), pick(rng, 50, 120, 5), pick(rng, 40, 100, 5)
    size = rng.choice([s for s in SIZES if 3 * edge(s) <= w])
    g = pick(rng, 15, min(a, b) - t - 2 * edge(size) - 2, 1) if min(a, b) - t - 2 * edge(size) - 2 >= 15 else 0.0
    gt = pick(rng, max(3, t - 1), t + 2)
    d.param("base_leg", a, "mm", "horizontal leg length", f"{num(a)} mm base leg")
    d.param("upright_leg", b, "mm", "vertical leg height", f"{num(b)} mm upright")
    d.param("width", w, "mm", "bracket width", f"{num(w)} mm wide")
    d.param("thickness", t, "mm", "plate thickness", f"{num(t)} mm plate")
    d.say("Overall dimensions", f"{d.title} from {num(t)} mm plate: {num(a)} mm base leg, {num(b)} mm upright, {num(w)} mm wide")
    corner: list[Point] = [
        (0, 0),
        ("base_leg", 0),
        ("base_leg", "thickness"),
        ("thickness", "thickness"),
        ("thickness", "upright_leg"),
        (0, "upright_leg"),
    ]
    _profile(d, corner, "width", "carries the load from the upright into the base")
    for what, v in (("base leg", a), ("upright", b), ("width", w)):
        d.need("extent", f"{what} {num(v)}", value=v)
    pair = rng.random() < 0.5 and w >= 60
    centre = 0.0
    if g:
        d.param("gusset_size", g, "mm", "gusset leg length", f"{num(g)} mm triangular")
        d.param("gusset_thickness", gt, "mm", "gusset thickness", f"{num(gt)} mm thick")
        triangle = [("thickness", "thickness"), ("thickness + gusset_size", "thickness"), ("thickness", "thickness + gusset_size")]
        plane: dict[str, Any] = {"ref": "XZ"}
        if pair:
            centre = pick(rng, w / 2 - gt / 2 - 6, w / 2 - gt / 2, 1)
            d.param(
                "gusset_offset", centre, "mm", "gusset centre from the middle of the width", f"{num(centre)} mm either side of the middle"
            )
            plane["offset"] = "gusset_offset"
            d.say("Features", f"a pair of {num(g)} mm triangular webs, {num(gt)} mm thick, {num(centre)} mm either side of the middle")
        else:
            d.say("Features", f"a single {num(g)} mm triangular web, {num(gt)} mm thick, on the centre plane")
        d.sketches.append({"id": "gusset", "plane": plane, "entities": [{"kind": "polygon", "points": [list(p) for p in triangle]}]})
        gusset = {
            "kind": "extrude",
            "id": "gusset",
            "name": "Gusset",
            "sketch": "gusset",
            "extent": "symmetric",
            "distance": "gusset_thickness",
        }
        d.features.append(gusset | {"intent": "stiffens the corner against bending"})
        if pair:
            mirror = {
                "kind": "pattern",
                "id": "gussets",
                "name": "Second gusset",
                "features": ["gusset"],
                "type": "mirror",
                "mirror_plane": "XZ",
            }
            d.features.append(mirror | {"intent": "a matching gusset at the other side"})
    _leg_holes(d, rng, size, t, w, gt if g else 0.0, centre if g and pair else None)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _leg_holes(d: Draft, rng: random.Random, size: str, t: float, w: float, gt: float, outer: float | None) -> None:
    if outer is None:
        lo, hi = (gt / 2 + head(size) / 2 + 3 if gt else head(size) / 2 + 3), w / 2 - edge(size)
    else:
        lo, hi = head(size) / 2 + 3, outer - gt / 2 - head(size) / 2 - 3
    if hi < lo:
        return
    s = pick(rng, 2 * lo, 2 * hi - 0.5, 1)
    kind = "counterbore" if t >= counterbore_depth(size) + 2 and rng.random() < 0.4 else "simple"
    b = bore(d, rng, size, kind)
    up = bore(d, rng, size, "simple", "upright_hole_diameter") if kind != "simple" else b
    d.param("hole_spacing", s, "mm", "hole centre distance across the width", f"{num(s)} mm apart")
    clear = " clear of the webs" if gt else ""
    if up is b:
        d.say("Holes and ports", f"per leg a pair of {b.words} bolt holes{clear}, {num(s)} mm apart, at mid-leg")
    else:
        d.say(
            "Holes and ports",
            f"base leg: a pair of {b.words} bolt holes; upright: a pair of {up.words} holes{clear}; both pairs {num(s)} mm apart",
        )
    ys = [("-hole_spacing / 2"), ("hole_spacing / 2")]
    base_x, up_z = "thickness + (base_leg - thickness) / 2", "thickness + (upright_leg - thickness) / 2"
    d.features.append(
        hole("base_holes", "Base holes", "body.bottom", [(base_x, y) for y in ys], **b.spec) | {"intent": "bolt the base down"}
    )
    d.features.append(
        hole("upright_holes", "Upright holes", "body.left", [(y, up_z) for y in ys], **up.spec) | {"intent": "fix the mounted part"}
    )
    if up is b:
        need_bores(d, b, 4)
    else:
        need_bores(d, b, 2, "base holes")
        need_bores(d, up, 2, "upright holes")
        d.need("counterbores", "2 counterbores", count=2)
    d.need("hole_axes", "holes in both legs", count=2)
    d.need("hole_spacing", f"{num(s)} mm apart", value=s)


def _z_bracket(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Z bracket", "Offset bracket", "Z-shaped bracket", "Joggle bracket")), "support")
    t, h, w = pick(rng, 2, 6, 0.5), pick(rng, 25, 80, 5), pick(rng, 20, 60, 5)
    size = rng.choice([s for s in SIZES if 2 * edge(s) <= w])
    f1, f2 = pick(rng, 2 * edge(size) + 2, 50, 1), pick(rng, 2 * edge(size) + 2, 50, 1)
    d.param("height", h, "mm", "overall height", f"overall height {num(h)} mm")
    d.param("width", w, "mm", "bracket width", f"width {num(w)} mm")
    d.param("thickness", t, "mm", "sheet thickness", f"{num(t)} mm stock")
    d.param("bottom_flange", f1, "mm", "bottom flange reach from the web", f"bottom flange {num(f1)} mm")
    d.param("top_flange", f2, "mm", "top flange reach from the web", f"top flange {num(f2)} mm")
    d.say("Overall dimensions", f"{d.title} bent from {num(t)} mm stock: overall height {num(h)} mm, width {num(w)} mm")
    d.say("Features", f"the bottom flange {num(f1)} mm runs left of the web and the top flange {num(f2)} mm runs right")
    points: list[Point] = [
        ("-bottom_flange", 0),
        ("thickness", 0),
        ("thickness", "height - thickness"),
        ("thickness + top_flange", "height - thickness"),
        ("thickness + top_flange", "height"),
        (0, "height"),
        (0, "thickness"),
        ("-bottom_flange", "thickness"),
    ]
    _profile(d, points, "width", "steps the mounting face up and across")
    b = bore(d, rng, size, "simple")
    d.say("Holes and ports", f"each flange has a single {b.words} hole at its midpoint")
    d.features.append(
        hole("bottom_hole", "Bottom flange hole", "body.bottom", [("-bottom_flange / 2", 0)], **b.spec) | {"intent": "fix to the base"}
    )
    d.features.append(
        hole("top_hole", "Top flange hole", "body.top", [("thickness + top_flange / 2", 0)], **b.spec) | {"intent": "fix the mounted part"}
    )
    need_bores(d, b, 2)
    d.need("extent", f"height {num(h)}", value=h)
    d.need("extent", f"width {num(w)}", value=w)
    d.need("extent", f"length {num(f1 + t + f2)}", value=f1 + t + f2)
    finish(d, rng, "sheet_metal" if t <= 3 else "milling_3axis")
    return d.spec()


def _hat(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Hat-section bracket", "Omega bracket", "Hat channel", "Raised channel bracket")), "support")
    t, c, h, length = pick(rng, 1.5, 4, 0.5), pick(rng, 20, 60, 5), pick(rng, 15, 50, 5), pick(rng, 25, 100, 5)
    size = rng.choice([s for s in SIZES if 2 * edge(s) <= length])
    f = pick(rng, 2 * edge(size) + 2, 40, 1)
    d.param("channel_width", c, "mm", "raised channel width outside", f"crown {num(c)} mm across the outside")
    d.param("channel_height", h, "mm", "overall height", f"{num(h)} mm overall height")
    d.param("flange", f, "mm", "flange reach from the channel", f"reaching {num(f)} mm outward")
    d.param("length", length, "mm", "length", f"{num(length)} mm along the channel")
    d.param("thickness", t, "mm", "sheet thickness", f"{num(t)} mm sheet")
    d.say("Overall dimensions", f"{d.title} formed from {num(t)} mm sheet, {num(length)} mm along the channel")
    d.say("Features", f"crown {num(c)} mm across the outside, {num(h)} mm overall height, side flanges reaching {num(f)} mm outward")
    hc, ht = "channel_width / 2", "channel_width / 2 - thickness"
    points: list[Point] = [
        (f"-{hc} - flange", 0),
        (f"-({ht})", 0),
        (f"-({ht})", "channel_height - thickness"),
        (ht, "channel_height - thickness"),
        (ht, 0),
        (f"{hc} + flange", 0),
        (f"{hc} + flange", "thickness"),
        (hc, "thickness"),
        (hc, "channel_height"),
        (f"-{hc}", "channel_height"),
        (f"-{hc}", "thickness"),
        (f"-{hc} - flange", "thickness"),
    ]
    _profile(d, points, "length", "a stiff raised mount from thin sheet")
    b = bore(d, rng, size, "simple")
    d.say("Holes and ports", f"a {b.words} hole centred on each side flange")
    pts = [(f"-({hc} + flange / 2)", 0), (f"{hc} + flange / 2", 0)]
    d.features.append(hole("flange_holes", "Flange holes", "body.bottom", pts, **b.spec) | {"intent": "fix the flanges down"})
    need_bores(d, b, 2)
    d.need("extent", f"overall width {num(c + 2 * f)}", value=c + 2 * f)
    d.need("extent", f"height {num(h)}", value=h)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("hole_spacing", f"holes {num(c + f)} apart", value=c + f)
    finish(d, rng, "sheet_metal")
    return d.spec()


def _clevis(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Clevis bracket", "Clevis mount", "Pivot bracket", "Fork bracket", "Lug bracket")), "support")
    size = rng.choice(("M5", "M6", "M8"))
    lug_l, lug_t, gap = pick(rng, 20, 50, 2), pick(rng, 4, 10), pick(rng, 8, 40, 2)
    pin = pick(rng, 5, lug_l / 3, 1)
    lug_h = pick(rng, lug_l / 2 + 1.5 * pin + 5, lug_l / 2 + 40, 1)
    base_t = pick(rng, 5, 12)
    span = gap + 2 * lug_t
    length = pick(rng, lug_l + 4 * edge(size) + 4, lug_l + 4 * edge(size) + 40, 5)
    width = pick(rng, max(span + 10, 2 * edge(size) + 10), span + 40, 5)
    s = pick(rng, lug_l + 2 * edge(size), length - 2 * edge(size) - 2.5, 1)
    d.param("base_length", length, "mm", "base length", f"{num(length)} x {num(width)} x {num(base_t)} mm base")
    d.param("base_width", width, "mm", "base width", f"{num(length)} x {num(width)} x {num(base_t)} mm base")
    d.param("base_thickness", base_t, "mm", "base thickness", f"{num(length)} x {num(width)} x {num(base_t)} mm base")
    d.param("lug_length", lug_l, "mm", "lug length along the base", f"{num(lug_l)} mm long")
    d.param("lug_thickness", lug_t, "mm", "lug thickness", f"{num(lug_t)} mm thick")
    d.param("lug_gap", gap, "mm", "gap between the lugs", f"{num(gap)} mm opening")
    d.param("lug_height", lug_h, "mm", "lug height above the base", f"rising {num(lug_h)} mm")
    d.param("pin_diameter", pin, "mm", "pin hole diameter", f"cross-drilled {num(pin)} mm")
    d.param("mount_spacing", s, "mm", "base hole centre distance", f"{num(s)} mm apart")
    d.say("Overall dimensions", f"{d.title}: a {num(length)} x {num(width)} x {num(base_t)} mm base")
    d.say(
        "Features",
        f"two upright ears {num(lug_t)} mm thick with a {num(gap)} mm opening between them, "
        f"each {num(lug_l)} mm long, rising {num(lug_h)} mm, with semicircular ends",
    )
    d.say("Holes and ports", f"the ears are cross-drilled {num(pin)} mm for the pin, on the axis of their semicircular ends")
    d.take(pin, pin)
    d.sketches.append(rect_sketch("base", "base_length", "base_width"))
    d.features.append(
        {
            "kind": "extrude",
            "id": "base",
            "name": "Base",
            "sketch": "base",
            "distance": "base_thickness",
            "intent": "bolts to the structure",
        }
    )
    top = "base_thickness + lug_height - lug_length / 2"
    path = {
        "kind": "path",
        "start": ["-lug_length / 2", "base_thickness"],
        "segments": [
            {"to": ["lug_length / 2", "base_thickness"]},
            {"to": ["lug_length / 2", top]},
            {"to": ["-lug_length / 2", top], "arc": "ccw", "radius": "lug_length / 2"},
        ],
    }
    d.sketches.append({"id": "lug", "plane": {"ref": "XZ"}, "entities": [path]})
    d.sketches.append(
        {
            "id": "slot",
            "plane": {"ref": "XZ"},
            "entities": [
                {
                    "kind": "rect",
                    "center": [0, "base_thickness + lug_height / 2 + 1"],
                    "width": "lug_length + 2",
                    "height": "lug_height + 2",
                }
            ],
        }
    )
    lugs = {
        "kind": "extrude",
        "id": "lugs",
        "name": "Lugs",
        "sketch": "lug",
        "extent": "symmetric",
        "distance": "lug_gap + 2 * lug_thickness",
    }
    d.features.append(lugs | {"intent": "carry the pin on both sides"})
    slot = {
        "kind": "extrude",
        "id": "lug_gap_cut",
        "name": "Gap between the lugs",
        "sketch": "slot",
        "mode": "cut",
        "extent": "symmetric",
        "distance": "lug_gap",
    }
    d.features.append(slot | {"intent": "room for the mating eye"})
    d.features.append(hole("pin_hole", "Pin hole", "lugs.front", [(0, top)], diameter="pin_diameter") | {"intent": "the pivot axis"})
    b = bore(d, rng, size, "simple")
    d.say("Holes and ports", f"base fixing: {b.many('two')} holes on its long centre line, {num(s)} mm apart, outside the ears")
    mounts = hole("mounts", "Base holes", "base.end", [("-mount_spacing / 2", 0), ("mount_spacing / 2", 0)], **b.spec)
    d.features.append(mounts | {"intent": "bolt the clevis down"})
    need_bores(d, b, 2, "base holes")
    d.need("holes", f"pin {num(pin)}", count=1, diameter_min=pin - 0.1, diameter_max=pin + 0.1)
    d.need("hole_axes", "pin crosswise to the base holes", count=2)
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"height {num(base_t + lug_h)}", value=base_t + lug_h)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _pedestal(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Pedestal mount", "Post mount", "Column base", "Standoff pedestal", "Pillar bracket")), "support")
    side, t = pick(rng, 60, 140, 5), pick(rng, 5, 12)
    size = rng.choice(("M5", "M6", "M8"))
    post_d = pick(rng, 15, max(15, side - 4 * edge(size) - 4), 1)
    post_h = pick(rng, 15, 100, 5)
    bore_d = pick(rng, 4, post_d / 3, 1)
    d.param("base_size", side, "mm", "square base side", f"{num(side)} x {num(side)} x {num(t)} mm")
    d.param("thickness", t, "mm", "base thickness", f"{num(side)} x {num(side)} x {num(t)} mm")
    d.param("post_diameter", post_d, "mm", "post diameter", f"{num(post_d)} mm in diameter")
    d.param("post_height", post_h, "mm", "post height above the base", f"rising {num(post_h)} mm")
    d.param("post_bore", bore_d, "mm", "hole down the post", f"bored {num(bore_d)} mm")
    d.take(bore_d, bore_d)
    d.say("Overall dimensions", f"{d.title}: square foot {num(side)} x {num(side)} x {num(t)} mm")
    d.say("Features", f"a central round column {num(post_d)} mm in diameter rising {num(post_h)} mm, bored {num(bore_d)} mm along its axis")
    d.sketches.append(rect_sketch("base", "base_size", "base_size"))
    d.features.append(
        {
            "kind": "extrude",
            "id": "base",
            "name": "Base",
            "sketch": "base",
            "distance": "thickness",
            "intent": "spreads the load on the floor",
        }
    )
    d.sketches.append(circle_sketch("post", "post_diameter", "base.end"))
    d.features.append(
        {"kind": "extrude", "id": "post", "name": "Post", "sketch": "post", "distance": "post_height", "intent": "raises the mounted part"}
    )
    d.features.append(
        hole("post_hole", "Post hole", "post.end", [(0, 0)], diameter="post_bore")
        | {"intent": "takes the rod or screw of the mounted part"}
    )
    margin = pick(rng, edge(size), max(edge(size), (side - post_d) / 4), 1)
    b = bore(d, rng, size, "simple")
    at, where = corner_grid(d, rng, ("base_size", side), ("base_size", side), margin, "hole")
    d.say("Holes and ports", f"the foot is fixed with {b.many(count_word(rng, 4))} holes near its corners, {where}")
    d.features.append(
        {
            "kind": "hole",
            "id": "corner_holes",
            "name": f"{size} corner holes",
            "plane": {"ref": "base.end"},
            "at": at,
            **b.spec,
            "intent": "anchor the base",
        }
    )
    need_bores(d, b, 4)
    d.need("holes", f"post hole {num(bore_d)}", count=1, diameter_min=bore_d - 0.1, diameter_max=bore_d + 0.1)
    d.need("extent", f"base {num(side)}", value=side)
    d.need("extent", f"height {num(t + post_h)}", value=t + post_h)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _lug(rng: random.Random) -> Spec:
    d = Draft(rng.choice(("Lifting lug", "Weld-on lug", "Shackle lug", "Padeye", "Tie-down lug")), "support")
    w, t = pick(rng, 40, 120, 5), pick(rng, 6, 20)
    h = pick(rng, w / 2 + 15, w + 40, 5)
    eye = pick(rng, 10, w / 3.2, 1)
    d.param("foot_width", w, "mm", "width at the foot", f"base {num(w)} mm across")
    d.param("height", h, "mm", "overall height", f"overall height {num(h)} mm")
    d.param("thickness", t, "mm", "plate thickness", f"{num(t)} mm plate")
    d.param("eye_diameter", eye, "mm", "eye hole diameter", f"eye hole {num(eye)} mm")
    d.say(
        "Overall dimensions",
        f"{d.title} profiled from {num(t)} mm plate: base {num(w)} mm across, overall height {num(h)} mm, semicircular head",
    )
    d.say("Holes and ports", f"eye hole {num(eye)} mm diameter, concentric with the head")
    top = "height - foot_width / 2"
    path = {
        "kind": "path",
        "start": ["-foot_width / 2", 0],
        "segments": [
            {"to": ["foot_width / 2", 0]},
            {"to": ["foot_width / 2", top]},
            {"to": ["-foot_width / 2", top], "arc": "ccw", "radius": "foot_width / 2"},
        ],
    }
    d.sketches.append({"id": "outline", "plane": {"ref": "XZ"}, "entities": [path]})
    body = {"kind": "extrude", "id": "body", "name": "Lug plate", "sketch": "outline", "extent": "symmetric", "distance": "thickness"}
    d.features.append(body | {"intent": "carries the lifting load into the weld at the foot"})
    d.features.append(hole("eye", "Eye", "body.front", [(0, top)], diameter="eye_diameter") | {"intent": "takes the shackle pin"})
    d.need("extent", f"width {num(w)}", value=w)
    d.need("extent", f"height {num(h)}", value=h)
    d.need("extent", f"plate {num(t)}", value=t)
    d.need("holes", f"eye {num(eye)}", count=1, diameter_min=eye - 0.1, diameter_max=eye + 0.1)
    finish(d, rng, "milling_3axis")
    return d.spec()
