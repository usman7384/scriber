from scriber_ir.expr import to_python
from scriber_ir.fasteners import boss_diameter, screw_holes
from scriber_ir.model import BossPattern, Expr, Groove, Keyway, Lid, Rib, ShellWithLid, SpurGear

HighLevel = SpurGear | Rib | BossPattern | ShellWithLid | Lid | Keyway | Groove


def high_level(f: HighLevel, on: list[str], at: str, enclosures: dict[str, ShellWithLid]) -> list[str]:
    match f:
        case SpurGear():
            hub = f"{_opt(f.hub_diameter)}, {_opt(f.hub_length)}"
            args = f"{_x(f.module)}, {_x(f.teeth)}, {_x(f.pressure_angle)}, {_x(f.backlash)}, {_x(f.face_width)}, {_opt(f.bore)}, {hub}"
            return [*on, f"    tool = _gear(pl, out, {_pt(f.center)}, {args})", *_add(f.id)]
        case Rib():
            args = f"{_pt(f.start)}, {_pt(f.end)}, {_x(f.thickness)}, {_x(f.height)}, 'rib {f.id}'"
            return [*on, f"    tool = _rib(part, pl, out, {args})", *_add(f.id), f"    part = _joined(part, 'rib {f.id}')"]
        case BossPattern():
            depth = _x(f.height) if f.hole_depth is None else _x(f.hole_depth)
            args = f"{at}, {_x(f.diameter)}, {_x(f.height)}, {_opt(f.hole_diameter)}, {depth}"
            holes = [] if f.hole_diameter is None else [f"    part = _apply(part, holes, 'cut', 'holes of {f.id}')"]
            joined = f"    part = _joined(part, 'boss_pattern {f.id}')"
            return [*on, f"    tool, holes = _bosses(pl, out, {args})", *_add(f.id), joined, *holes]
        case ShellWithLid():
            bosses = _bosses_args(f)
            size = f"{_x(f.width)}, {_x(f.depth)}, {_x(f.height)}, {_x(f.wall)}, {_x(f.floor)}"
            return [f"    tool = _enclosure({size}, {bosses[0]}, {bosses[1]}, {bosses[2]})", *_add(f.id)]
        case Lid():
            box = enclosures[f.of]
            bosses = _bosses_args(box)
            size = f"{_x(box.width)}, {_x(box.depth)}, {_x(box.wall)}, {_x(box.lid_thickness)}, {_x(box.lip_height)}"
            return [f"    tool = _lid({size}, {_x(box.clearance)}, {bosses[0]}, {bosses[2]})", *_add(f.id)]
        case Keyway():
            args = f"{f.on!r}, {_x(f.position)}, {_opt(f.length)}, {_opt(f.width)}, {_opt(f.depth)}, {_x(f.angle)}"
            return [f"    tool = _keyway(part, T[{f.of!r}][0], {args}, 'keyway {f.id}')", *_cut(f.id, "keyway")]
        case Groove():
            args = f"{f.on!r}, {_x(f.position)}, {_x(f.width)}, {_x(f.depth)}"
            return [f"    tool = _groove(part, T[{f.of!r}][0], {args}, 'groove {f.id}')", *_cut(f.id, "groove")]


def _bosses_args(f: ShellWithLid) -> tuple[str, str, str]:
    if f.screw is None:
        return "None", "None", "None"
    _, pilot, clearance = screw_holes(f.screw)
    diameter = repr(boss_diameter(f.screw)) if f.boss_diameter is None else _x(f.boss_diameter)
    return diameter, repr(pilot), repr(clearance)


def _add(fid: str) -> list[str]:
    return ["    part = _apply(part, tool, 'add')", f"    T[{fid!r}] = (tool, 'add', None)"]


def _cut(fid: str, what: str) -> list[str]:
    return [f"    part = _apply(part, tool, 'cut', '{what} {fid}')", f"    T[{fid!r}] = (tool, 'cut', None)"]


def _pt(p: tuple[Expr, Expr]) -> str:
    return f"({_x(p[0])}, {_x(p[1])})"


def _opt(e: Expr | None) -> str:
    return "None" if e is None else _x(e)


def _x(e: Expr) -> str:
    return to_python(e)
