import math


def involute(a: float) -> float:
    return math.tan(a) - a


# right flank of the tooth centred on +x, root to tip; standard addendum m, dedendum 1.25 m, radial below the base circle
def gear_flank(m: float, z: float, pa: float, backlash: float, points: int = 16) -> list[tuple[float, float]]:
    r, a = m * z / 2, math.radians(pa)
    rb, ra, rf = r * math.cos(a), r + m, r - 1.25 * m
    half = (math.pi * m / 2 - backlash / 2) / (2 * r) + involute(a)
    start = max(rb, rf)
    flank = [] if rf >= rb else [(rf * math.cos(half), -rf * math.sin(half))]
    for i in range(points + 1):
        rho = start + (ra - start) * i / points
        t = half - involute(math.acos(rb / rho))
        flank.append((rho * math.cos(t), -rho * math.sin(t)))
    return flank


def gear_problems(m: float, z: float, pa: float, backlash: float) -> list[str]:
    flank = gear_flank(m, z, pa, backlash, 1)
    tip, root = flank[-1], flank[0]
    problems = []
    if round(z) != z or z < 6:
        problems.append(f"teeth must be a whole number of at least 6, got {z:g}")
    if not 0 < pa < 45:
        problems.append(f"pressure_angle must be between 0 and 45 deg, got {pa:g}")
    if tip[1] >= 0:
        problems.append("the teeth come to a point before the tip circle; reduce the backlash or the pressure angle")
    if math.atan2(-root[1], root[0]) >= math.pi / z:
        problems.append("the tooth roots overlap; use more teeth or a smaller pressure angle")
    return problems
