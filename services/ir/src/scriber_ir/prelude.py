import inspect

from scriber_ir.airfoil import naca4

PRELUDE = """import math

from build123d import *


def sin(d): return math.sin(math.radians(d))
def cos(d): return math.cos(math.radians(d))
def tan(d): return math.tan(math.radians(d))
def sqrt(x): return math.sqrt(x)
def asin(x): return math.degrees(math.asin(x))
def acos(x): return math.degrees(math.acos(x))
def atan(x): return math.degrees(math.atan(x))
def atan2(y, x): return math.degrees(math.atan2(y, x))
def hypot(*v): return math.hypot(*v)


BASE = {"XY": Plane.XY, "XZ": Plane.XZ, "YZ": Plane.YZ}
AXES = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}
ALIASES = {"top": "+z", "bottom": "-z", "front": "-y", "back": "+y", "left": "-x", "right": "+x"}


def _datum(base, offset, about, angle):
    pl = BASE[base].offset(offset)
    return pl.rotated((angle, 0, 0)) if about == "x" else pl.rotated((0, angle, 0)) if about == "y" else pl


def _plane(origin, normal, x_dir):
    return Plane(origin=origin, z_dir=normal, x_dir=x_dir) if x_dir else Plane(origin=origin, z_dir=normal)


def _tube(points, od, wall, radius):
    path = FilletPolyline(*points, radius=radius) if radius > 0 and len(points) > 2 else Polyline(*points)
    start = Plane(origin=points[0], z_dir=path.tangent_at(0))
    ring = start * (Circle(od / 2) - Circle(od / 2 - wall)) if wall else start * Circle(od / 2)
    return sweep(ring, path=path, transition=Transition.ROUND)


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
        # a slanted face (a drafted side): sketch from its centre, x level along it, y up its slope
        x = Vector(0, 0, 1).cross(n) if abs(n.Z) < 0.999 else Vector(1, 0, 0)
        return Plane(origin=c, x_dir=x, z_dir=n).offset(offset), 1
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
    flat = [(f, f.normal_at(f.center()).dot(d)) for f in shape.faces() if f.geom_type == GeomType.PLANE]
    faces = [f for f, k in flat if k > 0.999]
    if not faces:
        # a drafted or tapered side still counts as facing that way, up to 30 degrees off
        near = [(f, k) for f, k in flat if k > 0.866]
        best = max((k for _, k in near), default=None)
        faces = [f for f, k in near if best is not None and k > best - 1e-6]
    if not faces:
        raise ValueError(f"{ref}: there is no flat face facing {name}, even within 30 degrees; sketch on a datum plane instead")
    return max(faces, key=lambda f: f.center().dot(d))


def _rect(w, h, r):
    return RectangleRounded(w, h, r) if r > 0 else Rectangle(w, h)


def _path(start, segments):
    points = [start] + [s[0] for s in segments]
    edges = [_segment(a, *s) for a, s in zip(points, segments)]
    if math.dist(points[-1], points[0]) > 1e-9:
        edges.append(Line(points[-1], points[0]))
    face = make_face(Wire(edges))
    for b, _, _, radius, *_ in segments:
        if radius > 0:
            corner = min(face.vertices(), key=lambda v: (v.X - b[0]) ** 2 + (v.Y - b[1]) ** 2)
            face = fillet(corner, radius=radius)
    return Sketch() + face


def _segment(a, b, arc, r, fillet, center=None):
    if arc == "none":
        return Line(a, b)
    if center is None:
        return RadiusArc(a, b, r if arc == "cw" else -r)
    # through the point halfway round, so sweeps over 180 degrees keep their side
    a0, a1 = (math.atan2(p[1] - center[1], p[0] - center[0]) for p in (a, b))
    sweep = (a1 - a0) % (2 * math.pi) if arc == "ccw" else -((a0 - a1) % (2 * math.pi))
    mid = a0 + sweep / 2
    radius = math.dist(a, center)
    return ThreePointArc(a, (center[0] + radius * math.cos(mid), center[1] + radius * math.sin(mid)), b)


def _grid(cx, cy, nx, ny, sx, sy):
    nx, ny = round(nx), round(ny)
    return [(cx + (i - (nx - 1) / 2) * sx, cy + (j - (ny - 1) / 2) * sy) for i in range(nx) for j in range(ny)]


def _polar(cx, cy, n, d, a0):
    n = round(n)
    return [(cx + d / 2 * cos(a0 + 360 * k / n), cy + d / 2 * sin(a0 + 360 * k / n)) for k in range(n)]


NOW = [None, None]
LOOSE = []


def _at(pid, fid):
    NOW[:] = [pid, fid]


def _apply(part, tool, mode, what="cut"):
    if part is None:
        if mode != "add":
            raise ValueError("the first feature must add material")
        return tool
    if mode == "add":
        return _pieces(part, part + tool, "adds a body that does not touch the rest of the part")
    if mode == "intersect":
        return part & tool
    # the overlap decides: OCCT's default volume of a B-spline body (a loft) can even rise after a cut
    if not (part & tool).solids():
        # OCCT can lose an overlap when faces or seams coincide exactly; a shift far below any tolerance finds it
        tool = Pos(1e-5, 1e-5, 1e-5) * tool
        # a tool that only touches the part now overlaps by the shift alone; a real overlap is far thicker
        if sum(s.volume for s in (part & tool).solids()) < 1e-3 * tool.volume:
            raise ValueError(f"{what} removed no material: it misses the part or points away from it")
    return _pieces(part, part - tool, "cuts the part into separate pieces")


def _pieces(before, after, what):
    if len(after.solids()) > len(before.solids()):
        LOOSE.append((*NOW, what))
    return after


def _extrude(part, sk, pl, out, mode, extent, d, d2, taper):
    n = pl.z_dir
    sk = _facing(sk, n)
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


def _wrap(part, owner, pl, flat, mode, depth):
    axis, radius = _touching_cylinder(part, owner, pl)
    out = pl.z_dir if (pl.origin - axis.position).dot(pl.z_dir) > 0 else -pl.z_dir
    a, b = axis.direction, out.cross(axis.direction)
    foot = axis.position + a * (pl.origin - axis.position).dot(a)
    inner, outer = (radius - depth, radius + 1) if mode == "cut" else (radius - 1, radius + depth)
    tools = []
    for face in flat.faces():
        if face.inner_wires():
            raise ValueError("a wrapped sketch takes outlines without holes; wrap the holes as a second feature")
        # 16 points along each edge, starting at its corner, so corners stay sharp
        points = [e.position_at(i / 16) for e in face.outer_wire().order_edges() for i in range(16)]
        local = [Vector(pl.from_local_coords((p.X, p.Y))) - foot for p in points]
        arcs = [(p.dot(a), p.dot(b) / radius) for p in local]
        if max(abs(t) for _, t in arcs) >= 1.5:
            raise ValueError("a wrapped sketch must stay within 85 degrees of where its plane touches the cylinder")
        # at distance r from the axis the outline is the touching one scaled across by r: its walls are radial; the inner
        # section sits deep enough that its corners clear the floor, which the ring below then cuts round
        low = inner * math.cos(max(abs(t) for _, t in arcs)) - 0.5
        rings = [[foot + a * z + b * (r * math.tan(t)) + out * r for z, t in arcs] for r in (low, outer)]
        sections = [Face(Wire.make_polygon(points, close=True)) for points in rings]
        lo, hi = min(z for z, _ in arcs) - 1, max(z for z, _ in arcs) + 1
        ring = Plane(origin=foot + a * lo, z_dir=a) * (Cylinder(outer, hi - lo, align=BOTTOM) - Cylinder(inner, hi - lo, align=BOTTOM))
        tools.append(loft(sections, ruled=True) & ring)
    tool = tools[0]
    for t in tools[1:]:
        tool = tool + t
    return tool


BOTTOM = (Align.CENTER, Align.CENTER, Align.MIN)


def _touching_cylinder(part, owner, pl):
    for f in part.faces():
        if f.geom_type != GeomType.CYLINDER or owner.distance_to(f.center()) > 1e-4:
            continue
        axis = f.axis_of_rotation
        gap = abs((pl.origin - axis.position).dot(pl.z_dir))
        if abs(axis.direction.dot(pl.z_dir)) < 1e-6 and abs(gap - f.radius) < 1e-4:
            return axis, f.radius
    raise ValueError("the sketch plane does not touch a cylinder of the feature it wraps onto; set it at the radius, parallel to the axis")


def _facing(sk, n):
    # a clockwise polygon's face points backwards and would extrude the wrong way, so every face is turned to the plane's normal
    faces = [f if f.normal_at().dot(n) >= 0 else -f for f in sk.faces()]
    return Sketch() + faces if faces else sk


def _sheet(pl, flat, t, k, bends, flanges):
    # the flat is cut along each bend's allowance strip; panels fold outward from the largest, which stays put
    bends = list(bends)
    for e0, e1, length, angle, up, r in flanges:
        flat, line = _flange_tab(flat, Vector(*e0, 0), Vector(*e1, 0), length, math.radians(angle) * (r + k * t))
        bends.append((*line, angle, up, r, None))
    folds, lines = [], []
    for a, b, angle, up, r, relief in bends:
        a, b = Vector(a[0], a[1], 0), Vector(b[0], b[1], 0)
        u = (b - a).normalized()
        allowance = math.radians(angle) * (r + k * t)
        strip = Plane(origin=(a + b) * 0.5, x_dir=u, z_dir=(0, 0, 1)) * Rectangle((b - a).length, allowance)
        if relief:
            for end, side in ((a, -1), (b, 1)):
                slot = Plane(origin=end + u * (side * relief / 2), x_dir=u, z_dir=(0, 0, 1)) * Rectangle(relief, allowance + 2 * (r + t))
                flat = flat - slot
        folds.append((a, u, Vector(-u.Y, u.X, 0), allowance, angle, up, r, strip))
        lines.append((a, b))
    FLATS.append((NOW[0], flat, [Edge.make_line(a, b) for a, b in lines]))
    rest = flat
    for f in folds:
        rest = rest - f[7]
    panels = rest.faces()
    if not panels:
        raise ValueError("the bend strips leave no flat panel; check the bend lines and the bend radius")
    base = max(range(len(panels)), key=lambda i: panels[i].area)
    moves, queue, body, used = {base: []}, [base], [], set()
    while queue:
        i = queue.pop(0)
        for j, (a, u, n, allowance, angle, up, r, strip) in enumerate(folds):
            side = _side(panels[i], a, lines[j][1], n, allowance)
            if side == 0:
                continue
            for o, p in enumerate(panels):
                if o in moves or _side(p, a, lines[j][1], n, allowance) != -side:
                    continue
                nc = n * -side
                used.add(j)
                moves[o] = moves[i] + [(a, u, nc, allowance, angle, up, r, t)]
                queue.append(o)
                ends = [v for v in (flat & strip).vertices() if p.distance_to(v) < 1e-6 or panels[i].distance_to(v) < 1e-6]
                piece = [(Vector(v.X, v.Y, v.Z) - a).dot(u) for v in ends]
                body.append(_moved(_bend(a, u, nc, allowance, angle, up, r, t, min(piece), max(piece)), moves[i]))
    body += [_moved(extrude(p, amount=t, dir=(0, 0, 1)), moves[i]) for i, p in enumerate(panels) if i in moves]
    stray = len(panels) - len(moves)
    if stray:
        raise ValueError(f"{stray} panel(s) of the flat pattern are not joined to the fixed one by a bend; check the bend lines")
    idle = [j + 1 for j in range(len(folds)) if j not in used]
    if idle:
        raise ValueError(f"bend {idle} does not split the flat: run its line edge to edge, or end it at cuts or reliefs")
    solid = body[0]
    for piece in body[1:]:
        solid = solid + piece
    return pl * solid


def _side(panel, a, b, n, allowance):
    # which long edge of a bend strip the panel runs along: +1 or -1, or 0 when it only meets the strip's ends
    mid = (a + b) * 0.5
    for side in (1, -1):
        if panel.distance_to(mid + n * (side * (allowance / 2 + 0.01))) < 1e-6:
            return side
    return 0


def _flange_tab(flat, a, b, length, allowance):
    u = (b - a).normalized()
    out = Vector(-u.Y, u.X, 0)
    mid = (a + b) * 0.5

    def inside(p):
        return any(f.distance_to(p) < 1e-9 for f in flat.faces())

    if inside(mid + out * 0.01):
        out = -out
    if inside(mid + out * 0.01) or not inside(mid - out * 0.01):
        raise ValueError(f"a flange edge from {tuple(a)[:2]} to {tuple(b)[:2]} is not on the flat pattern's outline")
    reach = allowance + length
    tab = Plane(origin=(a + b) * 0.5 + out * (reach / 2), x_dir=u, z_dir=(0, 0, 1)) * Rectangle((b - a).length, reach)
    shift = out * (allowance / 2)
    return flat + tab, (((a + shift).X, (a + shift).Y), ((b + shift).X, (b + shift).Y))


def _fold_axis(a, u, nc, allowance, up, r, t):
    edge = a - nc * (allowance / 2)
    z = Vector(0, 0, 1)
    return Axis(edge + z * (t + r), nc.cross(z)) if up else Axis(edge - z * r, z.cross(nc))


def _bend(a, u, nc, allowance, angle, up, r, t, s0, s1):
    edge = a - nc * (allowance / 2)
    z = Vector(0, 0, 1)
    section = Face(Wire.make_polygon([edge + u * s0, edge + u * s1, edge + u * s1 + z * t, edge + u * s0 + z * t], close=True))
    return revolve(section, axis=_fold_axis(a, u, nc, allowance, up, r, t), revolution_arc=angle)


def _moved(shape, moves):
    for a, u, nc, allowance, angle, up, r, t in reversed(moves):
        shape = shape.translate(-nc * allowance).rotate(_fold_axis(a, u, nc, allowance, up, r, t), angle)
    return shape


def _revolve(sk, pl, axis, offset, angle):
    if axis == "X":
        line = Axis(pl.origin + pl.y_dir * offset, pl.x_dir)
    else:
        line = Axis(pl.origin + pl.x_dir * offset, pl.y_dir)
    return revolve(sk, axis=line, revolution_arc=angle)


def _hole(part, pl, out, points, d, depth, cbd, cbdepth, csd, csangle, point, next_wall=False):
    up = pl.z_dir * (out or 1)
    through = depth is None and not next_wall
    box = part.bounding_box()
    tool = None
    for x, y in points:
        origin = pl.from_local_coords((x, y))
        _inside_outline(box, origin, up, d / 2, (x, y))
        length = 4 * box.diagonal if through else _past_wall(part, origin, -up, (x, y)) if depth is None else depth
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


def _past_wall(part, origin, down, at):
    # along the drill line: where it leaves the first wall, then halfway across the gap to the next one (or 1 mm out)
    hits = sorted(((p - origin).dot(down), n.dot(down)) for p, n in part.find_intersection_points(Axis(origin, down)))
    exits = [t for t, n in hits if t > 1e-6 and n > 0]
    if not exits:
        raise ValueError(f"the hole at {at} never leaves the material along its drill line; check its plane and direction")
    entries = [t for t, n in hits if t > exits[0] + 1e-6 and n < 0]
    return exits[0] + ((entries[0] - exits[0]) / 2 if entries else 1.0)


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
        tool, mode, facing = T[fid]
        if kind == "mirror":
            copies = [tool.mirror(BASE[plane])]
        elif kind == "linear":
            d = Vector(*AXES["+" + direction]) * spacing
            copies = [Pos(d.X * i, d.Y * i, d.Z * i) * tool for i in range(1, n)]
        else:
            copies = [Pos(c.X, c.Y, c.Z) * turn(step * i) * Pos(-c.X, -c.Y, -c.Z) * tool for i in range(1, n)]
        for copy in copies:
            part = _apply(part, copy, mode, f"pattern of {fid}")
        # later selectors on this feature see every copy, so a fillet "of" a patterned blade rounds all of them
        T[fid] = (Compound([tool, *copies]), mode, facing)
    return part


def _select(part, T, kind, of, meets, normal, parallel, convexity, extreme, geom="any", arc_radius=None, outline=False):
    items = list(part.edges() if kind == "edges" else part.faces())
    trail = [f"{len(items)} {kind} in the part"]
    if of != "part":
        tool = T[of][0]
        items = [i for i in items if tool.distance_to(i.center()) < 1e-4]
        trail.append(f"{len(items)} on {of!r}")
    if meets:
        other = T[meets][0]
        items = [i for i in items if other.distance_to(i.center()) < 1e-4]
        trail.append(f"{len(items)} where it meets {meets!r}")
    if normal != "any":
        d = _vec(normal)
        facing = [f for f in part.faces() if f.geom_type == GeomType.PLANE and f.normal_at(f.center()).dot(d) > 0.999]
        allowed = facing if kind == "faces" else [e for f in facing for e in (f.outer_wire().edges() if outline else f.edges())]
        items = [i for i in items if i in allowed]
        trail.append(f"{len(items)} on {'the outline of ' if outline else ''}flat faces facing {normal}")
    if parallel != "any":
        # a cylinder's seam is a straight line inside one face, not an edge anyone sees; a line between two faces is kept
        owners = {}
        for f in part.faces():
            for e in set(f.edges()):
                owners[e] = owners.get(e, 0) + 1
        line = {"x": Axis.X, "y": Axis.Y, "z": Axis.Z}[parallel] if isinstance(parallel, str) else Axis((0, 0, 0), _vec(parallel))
        items = [i for i in ShapeList(items).filter_by(line) if i.geom_type == GeomType.LINE and owners.get(i, 0) > 1]
        trail.append(f"{len(items)} straight and parallel to {parallel}")
    if geom != "any" and kind == "edges":
        items = [e for e in items if e.geom_type == {"line": GeomType.LINE, "circle": GeomType.CIRCLE}[geom]]
        trail.append(f"{len(items)} {geom}s")
    if arc_radius is not None and kind == "edges":
        items = [e for e in items if e.geom_type == GeomType.CIRCLE and abs(e.radius - arc_radius) < 1e-3]
        trail.append(f"{len(items)} circles or arcs of radius {arc_radius:g}")
    if convexity != "any" and kind == "edges":
        items = [e for e in items if e.is_interior == (convexity == "concave")]
        trail.append(f"{len(items)} {convexity}")
    if extreme != "any" and items:
        d = _vec(normal) if normal != "any" else Vector(0, 0, 1)
        keys = [i.center().dot(d) for i in items]
        target = max(keys) if extreme == "max" else min(keys)
        items = [i for i, k in zip(items, keys) if abs(k - target) < 1e-6]
    if not items:
        raise ValueError(f"the {kind} selector matched nothing ({', then '.join(trail)})")
    return items


def _vec(d):
    return Vector(*AXES[d]) if isinstance(d, str) else Vector(*d).normalized()


SKIPPED = []
FAILED = []
THREADS = []
FLATS = []


def _failed(fid, error):
    if isinstance(error, KeyError):
        # a lookup of an earlier feature's body: that feature failed, so this one has nothing to work on
        FAILED.append(f"feature {fid!r} depends on {error.args[0]!r}, which failed above; fix that first")
        return
    text = str(error) if isinstance(error, ValueError) else f"{type(error).__name__}: {error}"
    later = " (may follow from an earlier failure)" if FAILED else ""
    FAILED.append(f"feature {fid!r}{later}: {text}")


def _raise_failed():
    if FAILED:
        raise ValueError("; ".join(FAILED))


def _fillet(part, fid, select, radius):
    # an edge blend the kernel cannot make is left sharp and reported, so one fillet does not sink the whole part
    try:
        edges = select()
    except ValueError as e:
        SKIPPED.append((fid, str(e)))
        return part
    try:
        return fillet(edges, radius=radius)
    except (ValueError, RuntimeError):
        fits = _largest(lambda s: fillet(edges, radius=s), radius, "fillet")
        SKIPPED.append((fid, f"a {radius:g} mm fillet does not fit {_kinds(edges)}{fits}"))
        return part


def _chamfer(part, fid, select, length, length2):
    try:
        edges = select()
    except ValueError as e:
        SKIPPED.append((fid, str(e)))
        return part
    def make(s):
        return chamfer(edges, length=s) if length2 is None else chamfer(edges, length=s, length2=length2 * s / length)

    try:
        return make(length)
    except (ValueError, RuntimeError):
        SKIPPED.append((fid, f"a {length:g} mm chamfer does not fit {_kinds(edges)}{_largest(make, length, 'chamfer')}"))
        return part


def _draft(part, fid, select, pl, angle):
    try:
        faces = select()
    except ValueError as e:
        SKIPPED.append((fid, str(e)))
        return part
    try:
        return draft(faces, pl, angle)
    except (ValueError, RuntimeError):
        SKIPPED.append((fid, f"a {angle:g} degree draft does not work on these {len(faces)} faces; check that they meet the neutral plane"))
        return part


def _kinds(edges):
    count = {}
    for e in edges:
        k = e.geom_type.name.lower()
        count[k] = count.get(k, 0) + 1
    return f"these {len(edges)} edges (" + ", ".join(f"{n} {k}" for k, n in count.items()) + ")"


def _largest(make, size, what):
    # bisection on real attempts: the kernel's own estimate fails on the edges that need it most
    lo, hi = 0.0, size
    for _ in range(7):
        mid = (lo + hi) / 2
        try:
            make(mid)
            lo = mid
        except (ValueError, RuntimeError):
            hi = mid
    return f"; the largest that fits is about {lo:.2g} mm" if lo > 0.05 else f"; no {what} fits these edges, choose others"


def _spline(points):
    return Sketch() + make_face(Spline(*points, periodic=True))


def _hollow(sections, wall, ruled):
    # a skin of constant thickness: the loft of every section moved inward, taken out of the full loft
    outer = loft(sections, ruled=ruled)
    return outer - loft([_inset(s, wall) for s in sections], ruled=ruled)


def _inset(section, wall):
    try:
        return offset(section, amount=-wall)
    except RuntimeError:
        # OCCT cannot offset a closed spline: offset a fine polyline through it, then fit a spline back
        # (a 128-edge section makes the loft about 100 times slower)
        outline = section.faces()[0].outer_wire()
        fine = offset(make_face(Polyline(*[outline.position_at(i / 128) for i in range(128)], close=True)), amount=-wall)
        inner = fine.faces()[0].outer_wire()
        return make_face(Spline(*[inner.position_at(i / 48) for i in range(48)], periodic=True))


def _shell(part, faces, t):
    try:
        return part - offset(part, amount=-t) if not faces else offset(part, amount=-t, openings=faces)
    except (RuntimeError, ValueError) as e:
        raise ValueError(
            f"shell of {t} mm failed: the wall is thicker than the part's thinnest region or a curved face is in the way; "
            "use a thinner wall, open fewer faces, or for a lofted body use the loft's wall instead"
        ) from e
"""

AIRFOIL_PRELUDE = f"""

{inspect.getsource(naca4)}

def _airfoil(code, chord, le, twist):
    points = [(x * chord, y * chord) for x, y in naca4(code)]
    return Pos(*le) * Rot(0, 0, -twist) * Face(Wire([Spline(*points), Line(points[-1], points[0])]))
"""
