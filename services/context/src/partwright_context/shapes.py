import math

from partwright_ir import ShapeDescriptor


def distance(a: ShapeDescriptor, b: ShapeDescriptor) -> float:
    size = sum(abs(math.log((x + 1) / (y + 1))) for x, y in zip(a.bbox_sorted, b.bbox_sorted, strict=True)) / 3
    volume = abs(math.log((a.volume + 1) / (b.volume + 1))) / 3
    ha, hb = ({round(d, 1) for d in s.hole_diameters} for s in (a, b))
    holes = len(ha ^ hb) / max(1, len(ha | hb))
    return size + volume + holes


def similarity(a: ShapeDescriptor, b: ShapeDescriptor) -> float:
    return 1 / (1 + distance(a, b))
