import re

from scriber_ir.model import Param

# ISO 286-1 size steps (upper bound, mm) and values in micrometres
STEPS = (3, 6, 10, 18, 30, 50, 80, 120, 180, 250, 315, 400, 500)
IT = {
    5: (4, 5, 6, 8, 9, 11, 13, 15, 18, 20, 23, 25, 27),
    6: (6, 8, 9, 11, 13, 16, 19, 22, 25, 29, 32, 36, 40),
    7: (10, 12, 15, 18, 21, 25, 30, 35, 40, 46, 52, 57, 63),
    8: (14, 18, 22, 27, 33, 39, 46, 54, 63, 72, 81, 89, 97),
    9: (25, 30, 36, 43, 52, 62, 74, 87, 100, 115, 130, 140, 155),
    10: (40, 48, 58, 70, 84, 100, 120, 140, 160, 185, 210, 230, 250),
    11: (60, 75, 90, 110, 130, 160, 190, 220, 250, 290, 320, 360, 400),
}
# shaft upper deviations (f, g) and lower deviations (k for IT5-7, m, n, p); hole F and G mirror f and g
UPPER = {
    "f": (-6, -10, -13, -16, -20, -25, -30, -36, -43, -50, -56, -62, -68),
    "g": (-2, -4, -5, -6, -7, -9, -10, -12, -14, -15, -17, -18, -20),
}
LOWER = {
    "k": (0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 5),
    "m": (2, 4, 6, 7, 8, 9, 11, 13, 15, 17, 20, 21, 23),
    "n": (4, 8, 10, 12, 15, 17, 20, 23, 27, 31, 34, 37, 40),
    "p": (6, 12, 15, 18, 22, 26, 32, 37, 43, 50, 56, 62, 68),
}
FIT = re.compile(r"^(JS|js|[FGHfghkmnp])(\d{1,2})$")


def fit_limits(nominal: float, fit: str) -> tuple[float, float]:
    m = FIT.match(fit)
    if m is None or int(m[2]) not in IT:
        raise ValueError(
            f"fit {fit!r} is not in the table (holes F G H JS, shafts f g h js k m n p, grades 5 to 11); give tol_plus and tol_minus"
        )
    if not 0 < nominal <= STEPS[-1]:
        raise ValueError(f"fit {fit!r} covers sizes up to {STEPS[-1]} mm, not {nominal:g}")
    step = next(i for i, top in enumerate(STEPS) if nominal <= top)
    letter, grade = m[1], IT[int(m[2])][step]
    if letter.lower() == "js":
        low = -grade / 2
    elif letter == "H" or letter == "h":
        low = 0 if letter == "H" else -grade
    elif letter in ("F", "G"):
        low = -UPPER[letter.lower()][step]
    elif letter in UPPER:
        low = UPPER[letter][step] - grade
    else:
        low = 0 if letter == "k" and int(m[2]) > 7 else LOWER[letter][step]
    return round(low / 1000, 4), round((low + grade) / 1000, 4)


def limits(p: Param) -> tuple[float, float] | None:
    if p.fit is not None:
        low, high = fit_limits(p.value, p.fit)
    elif p.tol_plus is not None or p.tol_minus is not None:
        low, high = p.tol_minus or 0.0, p.tol_plus or 0.0
    else:
        return None
    return p.value + low, p.value + high
