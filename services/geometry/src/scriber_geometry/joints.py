from typing import Any

from build123d import Shape

from scriber_geometry.models import Interference, MateCheck

Mate = tuple[str, str, str]


def interferences(parts: dict[str, Shape[Any]]) -> list[Interference]:
    ids = list(parts)
    pairs = [(a, b) for i, a in enumerate(ids) for b in ids[i + 1 :] if _boxes_meet(parts[a], parts[b])]
    return [_common(a, b, parts[a], parts[b]) for a, b in pairs]


def mate_checks(parts: dict[str, Shape[Any]], mates: list[Mate], slack: dict[str, float]) -> list[MateCheck]:
    return [MateCheck(joint=j, parent=p, child=c, gap=parts[p].distance_to(parts[c]), slack=slack.get(j, 0.0)) for j, p, c in mates]


def _boxes_meet(a: Shape[Any], b: Shape[Any]) -> bool:
    ba, bb = a.bounding_box(), b.bounding_box()
    lo_a, hi_a, lo_b, hi_b = ((v.X, v.Y, v.Z) for v in (ba.min, ba.max, bb.min, bb.max))
    return all(lo_a[i] <= hi_b[i] and lo_b[i] <= hi_a[i] for i in range(3))


def _common(a: str, b: str, sa: Shape[Any], sb: Shape[Any]) -> Interference:
    common = sa.intersect(sb)
    solids = [] if common is None else common.solids()
    volume, area = sum(s.volume for s in solids), sum(s.area for s in solids)
    return Interference(a=a, b=b, volume=volume, depth=2 * volume / area if area else 0.0)
