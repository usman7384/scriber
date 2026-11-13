from typing import Any

from build123d import Shape

from scriber_geometry.models import Interference, MateCheck

Mate = tuple[str, str, str]


def interferences(parts: dict[str, Shape[Any]]) -> list[Interference]:
    # boxes are computed once and swept along x, so only parts whose boxes overlap reach the boolean
    boxes = {pid: _box(s) for pid, s in parts.items()}
    order = sorted(parts, key=lambda pid: boxes[pid][0][0])
    pairs = []
    for i, a in enumerate(order):
        for b in order[i + 1 :]:
            if boxes[b][0][0] > boxes[a][1][0]:
                break
            if _meet(boxes[a], boxes[b]):
                pairs.append((a, b))
    return [_common(a, b, parts[a], parts[b]) for a, b in pairs]


Box = tuple[tuple[float, float, float], tuple[float, float, float]]


def _box(s: Shape[Any]) -> Box:
    b = s.bounding_box()
    return (b.min.X, b.min.Y, b.min.Z), (b.max.X, b.max.Y, b.max.Z)


def _meet(a: Box, b: Box) -> bool:
    return all(a[0][i] <= b[1][i] and b[0][i] <= a[1][i] for i in range(3))


def mate_checks(parts: dict[str, Shape[Any]], mates: list[Mate], slack: dict[str, float]) -> list[MateCheck]:
    return [MateCheck(joint=j, parent=p, child=c, gap=parts[p].distance_to(parts[c]), slack=slack.get(j, 0.0)) for j, p, c in mates]


def _common(a: str, b: str, sa: Shape[Any], sb: Shape[Any]) -> Interference:
    common = sa.intersect(sb)
    solids = [] if common is None else common.solids()
    volume, area = sum(s.volume for s in solids), sum(s.area for s in solids)
    return Interference(a=a, b=b, volume=volume, depth=2 * volume / area if area else 0.0)
