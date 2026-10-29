import math

from build123d import *


def sin(d): return math.sin(math.radians(d))
def cos(d): return math.cos(math.radians(d))
def tan(d): return math.tan(math.radians(d))
def sqrt(x): return math.sqrt(x)


BASE = {"XY": Plane.XY, "XZ": Plane.XZ, "YZ": Plane.YZ}
AXES = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}
ALIASES = {"top": "+z", "bottom": "-z", "front": "-y", "back": "+y", "left": "-x", "right": "+x"}


def _datum(base, offset, about, angle):
    pl = BASE[base].offset(offset)
    return pl.rotated((angle, 0, 0)) if about == "x" else pl.rotated((0, angle, 0)) if about == "y" else pl


def _ref(part, T, D, ref, offset):
    if ref in BASE:
        return BASE[ref].offset(offset), 0
    if ref in D:
        return D[ref].offset(offset), 0
    owner, name = ref.split(".", 1)
    face = _face(part if owner == "part" else T[owner], name, ref)
    n, c = face.normal_at(face.center()), face.center()
    k = max(range(3), key=lambda i: abs((n.X, n.Y, n.Z)[i]))
    if abs((n.X, n.Y, n.Z)[k]) < 0.999:
        raise ValueError(f"face {ref} is not perpendicular to an axis; sketch on a datum plane instead")
    base = ("YZ", "XZ", "XY")[k]
    out = 1 if n.dot(BASE[base].z_dir) > 0 else -1
    position = (c.X, -c.Y, c.Z)[k]
    return BASE[base].offset(position + out * offset), out


def _face(entry, name, ref):
    shape, direction = (entry[0], entry[2]) if isinstance(entry, tuple) else (entry, None)
    if name in ("start", "end"):
        if direction is None:
            raise ValueError(f"{ref}: start and end faces exist only on extrudes")
        d = direction if name == "end" else -direction
    else:
        d = Vector(*AXES[ALIASES.get(name, name)])
    faces = [f for f in shape.faces() if f.geom_type == GeomType.PLANE and f.normal_at(f.center()).dot(d) > 0.999]
    if not faces:
        raise ValueError(f"{ref}: there is no flat face facing {name}")
    return max(faces, key=lambda f: f.center().dot(d))


def _rect(w, h, r):
    return RectangleRounded(w, h, r) if r > 0 else Rectangle(w, h)


def _path(start, segments):
    points = [start] + [s[0] for s in segments]
    edges = [Line(a, b) if arc == "none" else RadiusArc(a, b, r if arc == "cw" else -r) for a, (b, arc, r, _) in zip(points, segments)]
    if math.dist(points[-1], points[0]) > 1e-9:
        edges.append(Line(points[-1], points[0]))
    face = make_face(Wire(edges))
    for b, _, _, radius in segments:
        if radius > 0:
            corner = min(face.vertices(), key=lambda v: (v.X - b[0]) ** 2 + (v.Y - b[1]) ** 2)
            face = fillet(corner, radius=radius)
    return Sketch() + face


def _grid(cx, cy, nx, ny, sx, sy):
    nx, ny = round(nx), round(ny)
    return [(cx + (i - (nx - 1) / 2) * sx, cy + (j - (ny - 1) / 2) * sy) for i in range(nx) for j in range(ny)]


def _polar(cx, cy, n, d, a0):
    n = round(n)
    return [(cx + d / 2 * cos(a0 + 360 * k / n), cy + d / 2 * sin(a0 + 360 * k / n)) for k in range(n)]


def _apply(part, tool, mode, what="cut"):
    if part is None:
        if mode != "add":
            raise ValueError("the first feature must add material")
        return tool
    if mode == "add":
        return part + tool
    if mode == "intersect":
        return part & tool
    before = part.volume
    part = part - tool
    if part.volume >= before - 1e-9:
        raise ValueError(f"{what} removed no material: it misses the part or points away from it")
    return part


def _extrude(part, sk, pl, out, mode, extent, d, d2, taper):
    n = pl.z_dir
    sign = -out if mode == "cut" and out else out or 1
    if extent == "up_to_next":
        direction = n * sign
        return extrude(sk, dir=direction, until=Until.NEXT, target=part), direction
    if extent == "two_sided":
        return extrude(sk, amount=sign * d, taper=taper) + extrude(sk, amount=-sign * d2, taper=taper), n * sign
    big = 4 * part.bounding_box().diagonal if part is not None else 1000
    amount, both = {
        "blind": (sign * (d or 0), False),
        "symmetric": ((d or 0) / 2, True),
        "through_all": (sign * big, False) if out else (big, True),
    }[extent]
    return extrude(sk, amount=amount, both=both, taper=taper), n if amount >= 0 else -n


def _revolve(sk, pl, axis, offset, angle):
    if axis == "X":
        line = Axis(pl.origin + pl.y_dir * offset, pl.x_dir)
    else:
        line = Axis(pl.origin + pl.x_dir * offset, pl.y_dir)
    return revolve(sk, axis=line, revolution_arc=angle)


def _hole(part, pl, out, points, d, depth, cbd, cbdepth, csd, csangle, point):
    up = pl.z_dir * (out or 1)
    through = depth is None
    box = part.bounding_box()
    length = 4 * box.diagonal if through else depth
    tool = None
    for x, y in points:
        origin = pl.from_local_coords((x, y))
        _inside_outline(box, origin, up, d / 2, (x, y))
        hp = Plane(origin=origin, x_dir=pl.x_dir, z_dir=up)
        pieces = [hp * Cylinder(d / 2, length, align=(Align.CENTER, Align.CENTER, Align.CENTER if through else Align.MAX))]
        if point and not through:
            pieces.append(hp * Pos(0, 0, -depth) * Cone(0, d / 2, d / 2 / tan(59), align=(Align.CENTER, Align.CENTER, Align.MAX)))
        if cbd is not None:
            pieces.append(hp * Cylinder(cbd / 2, cbdepth, align=(Align.CENTER, Align.CENTER, Align.MAX)))
        if csd is not None:
            sink = (csd - d) / 2 / tan(csangle / 2)
            pieces.append(hp * Cone(d / 2, csd / 2, sink, align=(Align.CENTER, Align.CENTER, Align.MAX)))
        for piece in pieces:
            tool = piece if tool is None else tool + piece
    return tool


def _inside_outline(box, c, n, r, at):
    drill = "XYZ"[max(range(3), key=lambda i: abs((n.X, n.Y, n.Z)[i]))]
    for name, lo, hi, ci, ni in zip("XYZ", box.min, box.max, (c.X, c.Y, c.Z), (n.X, n.Y, n.Z)):
        if abs(ni) >= 0.5 or lo + r - 1e-6 <= ci <= hi - r + 1e-6:
            continue
        if hi - lo < 2 * r:
            where = f"the part is only {hi - lo:g} mm along {name}, less than the hole diameter"
            where += f"; this hole drills along {drill}, so its plane is probably wrong"
        else:
            where = f"its centre {name} must be between {lo + r:g} and {hi - r:g} (the hole drills along {drill})"
        raise ValueError(f"hole at ({at[0]:g}, {at[1]:g}) lies outside the part: {where}")


def _pattern(part, T, ids, kind, count, direction, spacing, axis, center, angle, plane):
    n = round(count)
    c = Vector(*center)
    turn = {"x": lambda a: Rot(a, 0, 0), "y": lambda a: Rot(0, a, 0), "z": lambda a: Rot(0, 0, a)}[axis]
    step = angle / n if abs(angle - 360) < 1e-9 else angle / max(n - 1, 1)
    for fid in ids:
        tool, mode, _ = T[fid]
        if kind == "mirror":
            copies = [tool.mirror(BASE[plane])]
        elif kind == "linear":
            d = Vector(*AXES["+" + direction]) * spacing
            copies = [Pos(d.X * i, d.Y * i, d.Z * i) * tool for i in range(1, n)]
        else:
            copies = [Pos(c.X, c.Y, c.Z) * turn(step * i) * Pos(-c.X, -c.Y, -c.Z) * tool for i in range(1, n)]
        for copy in copies:
            part = _apply(part, copy, mode, f"pattern of {fid}")
    return part


def _select(part, T, kind, of, normal, parallel, convexity, extreme):
    items = list(part.edges() if kind == "edges" else part.faces())
    if of != "part":
        tool = T[of][0]
        items = [i for i in items if tool.distance_to(i.center()) < 1e-4]
    if normal != "any":
        d = Vector(*AXES[normal])
        facing = [f for f in part.faces() if f.geom_type == GeomType.PLANE and f.normal_at(f.center()).dot(d) > 0.999]
        allowed = facing if kind == "faces" else [e for f in facing for e in f.edges()]
        items = [i for i in items if i in allowed]
    if parallel != "any":
        curved = [e for f in part.faces() if f.geom_type != GeomType.PLANE for e in f.edges()]
        line = {"x": Axis.X, "y": Axis.Y, "z": Axis.Z}[parallel]
        items = [i for i in ShapeList(items).filter_by(line) if i not in curved]
    if convexity != "any" and kind == "edges":
        items = [e for e in items if e.is_interior == (convexity == "concave")]
    if extreme != "any" and items:
        d = Vector(*AXES[normal]) if normal != "any" else Vector(0, 0, 1)
        keys = [i.center().dot(d) for i in items]
        target = max(keys) if extreme == "max" else min(keys)
        items = [i for i, k in zip(items, keys) if abs(k - target) < 1e-6]
    if not items:
        raise ValueError(f"the {kind} selector matched nothing")
    return items


def _shell(part, faces, t):
    if not faces:
        return part - offset(part, amount=-t)
    return offset(part, amount=-t, openings=faces)


P = {

}


def part_0():
    part = None
    T = {}
    D = {}
    # body_s Body
    pl, out = _ref(part, T, D, 'XY', 0.0)
    sk = pl * (Pos(0.0, 0.0) * _rect(60.0, 40.0, 0.0))
    tool, direction = _extrude(part, sk, pl, out, 'add', 'blind', 5.0, None, 0.0)
    part = _apply(part, tool, 'add')
    T['body_s'] = (tool, 'add', direction)
    # h Hole
    pl, out = _ref(part, T, D, 'XY', 5.0)
    tool = _hole(part, pl, out, [(20.0, 0.0)], 10.0, None, None, None, None, 90.0, False)
    part = _apply(part, tool, 'cut', 'hole h')
    T['h'] = (tool, 'cut', None)
    part.label = 'P'
    return part


def build():
    return {'p': part_0()}
