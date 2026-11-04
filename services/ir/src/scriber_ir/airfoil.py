import math


# unit chord, upper TE -> LE -> lower TE, cosine spacing, open TE; embedded verbatim in model code, so math-only and comment-free
def naca4(code: str, points: int = 60) -> list[tuple[float, float]]:
    m, p, t = int(code[0]) / 100, int(code[1]) / 10, int(code[2:]) / 100
    upper, lower = [], []
    for i in range(points + 1):
        x = (1 - math.cos(math.pi * i / points)) / 2
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1015 * x**4)
        if m == 0:
            yc, slope = 0.0, 0.0
        elif x < p:
            yc, slope = m / p**2 * (2 * p * x - x**2), 2 * m / p**2 * (p - x)
        else:
            yc, slope = m / (1 - p) ** 2 * (1 - 2 * p + 2 * p * x - x**2), 2 * m / (1 - p) ** 2 * (p - x)
        theta = math.atan(slope)
        upper.append((x - yt * math.sin(theta), yc + yt * math.cos(theta)))
        lower.append((x + yt * math.sin(theta), yc - yt * math.cos(theta)))
    return upper[::-1] + lower[1:]
