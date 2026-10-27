import random

from partwright_agent import EN1092_PN16, EXTRUSION, NEMA
from partwright_training.fasteners import clearance, edge
from partwright_training.holes import bore, need_bores
from partwright_training.spec import Draft, Spec, circle_sketch, count_word, finish, hole, num, pick, rect_sketch

# the sizes the eval sets use stay out of training: DN50, NEMA 17 and 2020 (M1), NEMA 23 (grounded)
FLANGES = [dn for dn in EN1092_PN16 if dn != 50]
MOTORS = [n for n in NEMA if n not in (17, 23)]
SERIES = [s for s in EXTRUSION if s != 20]
# EN 10220 series 1 pipe outside diameters
PIPE_OD = {15: 21.3, 20: 26.9, 25: 33.7, 32: 42.4, 40: 48.3, 80: 88.9, 100: 114.3}
FLANGE_REQUESTS = (
    "EN 1092-1 PN16 flat flange DN{dn}, {t} mm thick, {bore} mm bore, drilled to the standard",
    "Flat flange DN{dn} PN16 per EN 1092-1, {t} mm thick, {bore} mm bore, standard bolt pattern",
    "Plate flange for DN{dn} pipe, PN16 to EN 1092-1, {t} mm thick with a {bore} mm bore and the standard holes",
)
MOTOR_REQUESTS = (
    "Mounting plate for a NEMA {n} stepper, {size}, with the standard screw holes and a pilot hole",
    "NEMA {n} motor plate {size}: standard mounting pattern plus the centring pilot hole",
    "Plate to hold a NEMA {n} motor, {size}, with holes for the motor screws and its pilot",
)
EXTRUSION_REQUESTS = (
    "Flat connector for {profile} extrusion profile, {size}, {holes} holes on the {s} mm slot centres",
    "Splice plate joining two lengths of {profile} aluminium profile, {size}, with {holes} holes on the {s} mm slot centres",
    "{profile} extrusion strap, {size}, {holes} holes on the {s} mm slot centres",
)


def standard(rng: random.Random) -> Spec:
    return rng.choice((_flange, _motor_plate, _extrusion_plate))(rng)


def _flange(rng: random.Random) -> Spec:
    dn = rng.choice(FLANGES)
    od, pcd, n, hole_d, _ = EN1092_PN16[dn]
    ref = f"EN 1092-1 PN16 DN{dn}"
    d = Draft(f"DN{dn} flange", "standard")
    # standard flanges sit closer to the rim than the default 1.5 x D hole-edge rule allows
    d.exempt = ("min_hole_edge_ratio",)
    thick, centre = pick(rng, 12, 24), round(PIPE_OD[dn] + rng.choice((0.0, 0.5, 1.0)), 1)
    d.param("thickness", thick, "mm", "flange thickness", f"{num(thick)} mm thick")
    d.param("bore_diameter", centre, "mm", "centre bore", f"{num(centre)} mm bore")
    d.standard("outer_diameter", od, "mm", "flange outer diameter", ref)
    d.standard("bolt_circle_diameter", pcd, "mm", "bolt circle diameter", ref)
    d.standard("bolt_count", n, "", "number of bolt holes", ref)
    d.standard("bolt_hole_diameter", hole_d, "mm", "bolt hole diameter", ref)
    d.say("Overall dimensions", rng.choice(FLANGE_REQUESTS).format(dn=dn, t=num(thick), bore=num(centre)))
    d.sketches.append(circle_sketch("disc", "outer_diameter", "XY"))
    d.features.append({"kind": "extrude", "id": "flange", "name": "Flange", "sketch": "disc", "distance": "thickness"})
    at = {"kind": "polar", "count": "bolt_count", "diameter": "bolt_circle_diameter"}
    bolts = {"kind": "hole", "id": "bolt_holes", "name": "Bolt holes", "plane": {"ref": "flange.top"}, "at": at}
    d.features.append({**bolts, "diameter": "bolt_hole_diameter"})
    d.features.append(hole("bore", "Bore", "flange.top", [(0, 0)], diameter="bore_diameter"))
    d.need("extent", f"outer diameter {od}", value=od, tolerance=0.5)
    d.need("extent", f"thickness {num(thick)}", value=thick)
    d.need("holes", f"{n} bolt holes {hole_d}", count=n, diameter_min=hole_d - 0.1, diameter_max=hole_d + 0.1)
    d.need("hole_spacing", f"PCD {pcd} across", value=pcd, tolerance=0.5, diameter_min=hole_d - 0.1, diameter_max=hole_d + 0.1)
    d.need("holes", f"{num(centre)} mm bore", count=1, diameter_min=centre - 0.1, diameter_max=centre + 0.1)
    return d.spec()


def _motor_plate(rng: random.Random) -> Spec:
    n = rng.choice(MOTORS)
    face, square, pilot, screw = NEMA[n]
    ref = f"NEMA {n}"
    d = Draft(f"NEMA {n} motor plate", "standard")
    side, thick = pick(rng, max(face + 4, square + 2 * edge(screw)), face + 40, 1), pick(rng, 3, 8)
    size = f"{num(side)} x {num(side)} x {num(thick)} mm"
    d.param("plate_size", side, "mm", "plate side length", size)
    d.param("thickness", thick, "mm", "plate thickness", size)
    d.standard("hole_square", square, "mm", "motor screw hole square", ref)
    d.standard("pilot_diameter", pilot, "mm", "centring pilot hole", ref)
    d.say("Overall dimensions", rng.choice(MOTOR_REQUESTS).format(n=n, size=size))
    d.sketches.append(rect_sketch("outline", "plate_size", "plate_size"))
    d.features.append({"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "outline", "distance": "thickness"})
    at = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "hole_square", "spacing_y": "hole_square"}
    d.features.append({"kind": "hole", "id": "screw_holes", "name": f"{screw} screw holes", "plane": {"ref": "plate.top"}, "at": at})
    d.features[-1]["fastener"] = screw
    d.features.append(hole("pilot", "Pilot hole", "plate.top", [(0, 0)], diameter="pilot_diameter"))
    lo, hi = clearance(screw)
    d.need("extent", f"side {num(side)}", value=side)
    d.need("extent", f"thickness {num(thick)}", value=thick)
    d.need("holes", f"four {screw} clearance", count=4, diameter_min=lo, diameter_max=hi)
    d.need("hole_spacing", f"{square:g} mm square", value=square, diameter_min=lo, diameter_max=hi)
    d.need("holes", f"pilot {pilot:g}", count=1, diameter_min=pilot - 0.1, diameter_max=pilot + 0.1)
    finish(d, rng, "milling_3axis")
    return d.spec()


def _extrusion_plate(rng: random.Random) -> Spec:
    s = rng.choice(SERIES)
    screw = EXTRUSION[s][1]
    slots, rows = rng.randint(2, 5), rng.choice((1, 1, 2))
    length, width, thick = slots * s, rows * s, pick(rng, 4, 8)
    d = Draft(rng.choice(("Extrusion joining plate", "Splice plate", "Profile connector", "Extrusion strap")), "standard")
    size = f"{num(length)} x {num(width)} x {num(thick)} mm"
    d.param("length", length, "mm", "plate length", size)
    d.param("width", width, "mm", "plate width", size)
    d.param("thickness", thick, "mm", "plate thickness", size)
    d.param("slot_pitch", s, "mm", "extrusion slot centres", f"{s} mm slot centres")
    b = bore(d, rng, screw, "simple")
    profile = f"{s}{s * rows}"
    holes = b.many(count_word(rng, slots * rows))
    d.say("Overall dimensions", rng.choice(EXTRUSION_REQUESTS).format(profile=profile, size=size, holes=holes, s=s))
    d.sketches.append(rect_sketch("outline", "length", "width"))
    d.features.append({"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "outline", "distance": "thickness"})
    counts = {"count_x": "length / slot_pitch", "count_y": "width / slot_pitch"}
    at = {"kind": "grid", **counts, "spacing_x": "slot_pitch", "spacing_y": "slot_pitch"}
    d.features.append({"kind": "hole", "id": "slot_holes", "name": "Slot holes", "plane": {"ref": "plate.top"}, "at": at, **b.spec})
    d.need("extent", f"length {num(length)}", value=length)
    d.need("extent", f"width {num(width)}", value=width)
    d.need("extent", f"thickness {num(thick)}", value=thick)
    need_bores(d, b, slots * rows)
    d.need("hole_spacing", f"{s} mm slot centres", value=s)
    finish(d, rng, "milling_3axis")
    return d.spec()
