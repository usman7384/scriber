import inspect

from partwright_ir import keys
from partwright_ir.gear import gear_flank, involute

FEATURE_PRELUDE = f"""

UP = (Align.CENTER, Align.CENTER, Align.MIN)
DOWN = (Align.CENTER, Align.CENTER, Align.MAX)


{inspect.getsource(involute)}

{inspect.getsource(gear_flank)}

{inspect.getsource(keys)}

def _joined(part, what):
    if len(part.solids()) > 1:
        raise ValueError(f"{{what}} does not touch the part")
    return part


def _turn(p, deg):
    return (p[0] * cos(deg) - p[1] * sin(deg), p[0] * sin(deg) + p[1] * cos(deg))


def _gear(pl, out, c, m, z, pa, backlash, width, bore, hub_d, hub_l):
    z = round(z)
    right = gear_flank(m, z, pa, backlash)
    left = [(x, -y) for x, y in reversed(right)]
    radial = m * z / 2 - 1.25 * m < m * z / 2 * cos(pa)
    teeth = [([_turn(p, 360 * k / z) for p in right], [_turn(p, 360 * k / z) for p in left]) for k in range(z)]
    edges = []
    for k, (r, l) in enumerate(teeth):
        tip, root = _turn((m * z / 2 + m, 0), 360 * k / z), _turn((m * z / 2 - 1.25 * m, 0), 360 * (k + 0.5) / z)
        rising = [Line(r[0], r[1]), Spline(*r[1:])] if radial else [Spline(*r)]
        falling = [Spline(*l[:-1]), Line(l[-2], l[-1])] if radial else [Spline(*l)]
        edges += [*rising, ThreePointArc(r[-1], tip, l[0]), *falling, ThreePointArc(l[-1], root, teeth[(k + 1) % z][0][0])]
    body = extrude(make_face(Wire(edges)), width)
    if hub_d is not None:
        body = body + Pos(0, 0, width) * Cylinder(hub_d / 2, hub_l, align=UP)
    if bore is not None:
        body = body - Cylinder(bore / 2, 3 * (width + (hub_l or 0)))
    return Plane(origin=pl.from_local_coords(c), x_dir=pl.x_dir, z_dir=pl.z_dir * (out or 1)) * body


def _rib(part, pl, out, start, end, t, h, what):
    a, b = pl.from_local_coords(start), pl.from_local_coords(end)
    rp = Plane(origin=(a + b) * 0.5, x_dir=b - a, z_dir=pl.z_dir * (out or 1))
    slab = rp * Box((b - a).length, t, h, align=UP)
    probe = rp.from_local_coords((0, 0, h / 2))
    pieces = [s for s in (slab - part).solids() if s.is_inside(probe)]
    if not pieces:
        raise ValueError(f"{{what}}: the middle of its line is inside material; draw the line where the rib should stand")
    return pieces[0]


def _bosses(pl, out, points, d, h, hole_d, hole_depth):
    tool, holes = None, None
    for x, y in points:
        bp = Plane(origin=pl.from_local_coords((x, y)), x_dir=pl.x_dir, z_dir=pl.z_dir * (out or 1))
        boss = bp * Cylinder(d / 2, h, align=UP)
        tool = boss if tool is None else tool + boss
        if hole_d is not None:
            hole = bp * Pos(0, 0, h) * Cylinder(hole_d / 2, hole_depth, align=DOWN)
            holes = hole if holes is None else holes + hole
    return tool, holes


def _corners(w, d, wall, bd):
    x, y = (w - wall - bd) / 2, (d - wall - bd) / 2
    return [(sx * x, sy * y) for sx in (-1, 1) for sy in (-1, 1)]


def _enclosure(w, d, h, wall, floor, bd, pilot):
    box = Box(w, d, h, align=UP) - Pos(0, 0, floor) * Box(w - 2 * wall, d - 2 * wall, h, align=UP)
    if bd is None:
        return box
    for x, y in _corners(w, d, wall, bd):
        box = box + Pos(x, y, floor) * Cylinder(bd / 2, h - floor, align=UP)
        box = box - Pos(x, y, h + 1) * Cylinder(pilot / 2, h - floor + 1, align=DOWN)
    return box


def _lid(w, d, wall, t, lip, gap, bd, clear):
    iw, idp = w - 2 * wall - 2 * gap, d - 2 * wall - 2 * gap
    ring = Box(iw, idp, lip, align=UP) - Box(iw - 2 * wall, idp - 2 * wall, lip, align=UP)
    lid = Box(w, d, t, align=UP) + Pos(0, 0, -lip) * ring
    if bd is None:
        return lid
    for x, y in _corners(w, d, wall, bd):
        lid = lid - Pos(x, y, -lip) * Cylinder(bd / 2 + gap, lip, align=UP)
        lid = lid - Pos(x, y, t / 2) * Cylinder(clear / 2, 3 * t)
    return lid


def _surface(part, tool, on, position, length, what):
    found = []
    for f in part.faces():
        if f.geom_type != GeomType.CYLINDER or tool.distance_to(f.position_at(0.5, 0.5)) > 1e-4:
            continue
        p, axis = f.position_at(0.5, 0.5), f.axis_of_rotation
        d = axis.direction if max((axis.direction.X, axis.direction.Y, axis.direction.Z), key=abs) > 0 else -axis.direction
        foot = axis.position - d * axis.position.dot(d)
        if (f.normal_at(p).dot(p - foot - d * p.dot(d)) > 0) != (on == "shaft"):
            continue
        ts = [Vector(v).dot(d) for v in f.vertices()]
        found.append((f.radius, foot, d, min(ts), max(ts)))
    if not found:
        raise ValueError(f"{{what}}: the feature it refers to has no cylindrical {{on}} surface")
    start = min(c[3] for c in found) + position
    fits = [c for c in found if c[3] - 1e-6 <= start < c[4] and (length is None or start + length <= c[4] + 1e-6)]
    if not fits:
        raise ValueError(f"{{what}}: no {{on}} surface runs from {{position:g}} over the length asked for")
    r, foot, d, _, hi = (max if on == "shaft" else min)(fits, key=lambda c: c[0])
    return r, foot, d, start, hi if length is None else start + length


def _keyway(part, tool, on, position, length, width, depth, angle, what):
    r, foot, d, a, b = _surface(part, tool, on, position, length, what)
    if width is None or depth is None:
        b6885, t1, t2 = din6885(2 * r)
        width = b6885 if width is None else width
        depth = (t1 if on == "shaft" else t2) if depth is None else depth
    ref = Vector(1, 0, 0) if abs(d.Z) > 0.9 else Vector(0, 0, 1)
    ref = (ref - d * ref.dot(d)).normalized()
    radial = ref * cos(angle) + d.cross(ref) * sin(angle)
    base = r - depth if on == "shaft" else 0
    kp = Plane(origin=foot + d * ((a + b) / 2) + radial * base, x_dir=d, z_dir=radial)
    if on == "bore" or length is None:
        return kp * Box(b - a, width, r + depth, align=UP)
    return extrude(kp * SlotOverall(b - a, width), amount=r + depth)


def _groove(part, tool, on, position, width, depth, what):
    r, foot, d, a, _ = _surface(part, tool, on, position, width, what)
    inner = r - depth if on == "shaft" else r / 2
    return Plane(origin=foot + d * a, z_dir=d) * (Cylinder(r + depth, width, align=UP) - Cylinder(inner, width, align=UP))
"""
