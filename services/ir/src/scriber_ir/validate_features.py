from collections.abc import Iterator

from scriber_ir.expr import ExprError, evaluate
from scriber_ir.fasteners import boss_diameter, parse, screw_holes
from scriber_ir.gear import gear_problems
from scriber_ir.model import (
    BossPattern,
    Expr,
    Extrude,
    Feature,
    Groove,
    Hole,
    Keyway,
    Revolve,
    Rib,
    ShellWithLid,
    SpurGear,
)

SURFACE_SOURCES = (Extrude, Revolve, Hole, SpurGear, BossPattern)


def high_level_errors(f: Feature, seen: dict[str, Feature], values: dict[str, float]) -> Iterator[str]:
    match f:
        case SpurGear():
            yield from _gear(f, values)
        case Rib():
            yield from _rib(f, seen, values)
        case BossPattern():
            yield from _bosses(f, values)
        case ShellWithLid():
            yield from _enclosure(f, values)
        case Keyway() | Groove():
            source = seen.get(f.of)
            if not isinstance(source, SURFACE_SOURCES):
                usable = [fid for fid, s in seen.items() if isinstance(s, SURFACE_SOURCES)]
                yield f"{f.of!r} is not an earlier extrude, revolve, hole, spur_gear or boss_pattern; usable so far: {usable}"


def _gear(f: SpurGear, values: dict[str, float]) -> Iterator[str]:
    v = _numbers(values, m=f.module, z=f.teeth, pa=f.pressure_angle, backlash=f.backlash)
    bore, hub = _maybe(values, f.bore), _maybe(values, f.hub_diameter)
    if v is None or min(v["m"], v["z"], v["pa"]) <= 0:
        return
    if v["backlash"] < 0:
        yield "backlash must be >= 0"
    yield from gear_problems(v["m"], v["z"], v["pa"], max(v["backlash"], 0))
    root = v["m"] * (v["z"] - 2.5)
    if bore is not None and bore >= root:
        yield f"bore {bore:g} must be smaller than the root diameter m(z - 2.5) = {root:g}"
    if (f.hub_diameter is None) != (f.hub_length is None):
        yield "give both hub_diameter and hub_length, or neither"
    if hub is not None and bore is not None and hub <= bore:
        yield f"hub_diameter {hub:g} must be larger than the bore {bore:g}"


def _rib(f: Rib, seen: dict[str, Feature], values: dict[str, float]) -> Iterator[str]:
    if not seen:
        yield "a rib needs an earlier feature to stand on"
    v = _numbers(values, x0=f.start[0], y0=f.start[1], x1=f.end[0], y1=f.end[1])
    if v is not None and (v["x0"], v["y0"]) == (v["x1"], v["y1"]):
        yield "start and end are the same point"


def _bosses(f: BossPattern, values: dict[str, float]) -> Iterator[str]:
    d, hole = _maybe(values, f.diameter), _maybe(values, f.hole_diameter)
    if d is not None and hole is not None and hole >= d:
        yield f"hole_diameter {hole:g} must be smaller than the boss diameter {d:g}"
    if f.hole_depth is not None and f.hole_diameter is None:
        yield "hole_depth needs a hole_diameter"


def _enclosure(f: ShellWithLid, values: dict[str, float]) -> Iterator[str]:
    v = _numbers(values, w=f.width, d=f.depth, h=f.height, wall=f.wall, floor=f.floor, lip=f.lip_height, gap=f.clearance)
    if v is None:
        return
    if 4 * v["wall"] + 2 * v["gap"] >= min(v["w"], v["d"]):
        yield "the walls, the lid's lip (as thick as the wall) and the clearance leave no opening; reduce wall or clearance"
    if v["floor"] >= v["h"]:
        yield f"floor {v['floor']:g} must be less than the height {v['h']:g}"
    elif v["lip"] >= v["h"] - v["floor"]:
        yield f"lip_height {v['lip']:g} must be less than the inside depth {v['h'] - v['floor']:g}"
    if f.screw is None:
        if f.boss_diameter is not None:
            yield "boss_diameter needs a screw such as 'M3'"
        return
    if parse(f.screw) is None:
        yield f"unknown screw {f.screw!r}; use M2 to M30"
        return
    _, _, clearance = screw_holes(f.screw)
    bd = _maybe(values, f.boss_diameter) or boss_diameter(f.screw)
    if bd <= max(v["wall"], clearance):
        yield f"boss_diameter {bd:g} must exceed the wall {v['wall']:g} and the {f.screw} clearance hole {clearance:g}"


def _numbers(values: dict[str, float], **exprs: Expr) -> dict[str, float] | None:
    try:
        return {k: evaluate(e, values) for k, e in exprs.items()}
    except ExprError:
        return None  # the bad expression is reported where it is written


def _maybe(values: dict[str, float], e: Expr | None) -> float | None:
    found = None if e is None else _numbers(values, e=e)
    return None if found is None else found["e"]
