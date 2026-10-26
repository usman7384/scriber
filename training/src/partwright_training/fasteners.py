# metric size -> ISO 273 clearance (close, loose), coarse pitch, ISO 4762 head diameter; mirrors the IR table for the sizes we sample
FASTENERS: dict[str, tuple[float, float, float, float]] = {
    "M3": (3.2, 3.6, 0.5, 5.5),
    "M4": (4.3, 4.8, 0.7, 7.0),
    "M5": (5.3, 5.8, 0.8, 8.5),
    "M6": (6.4, 7.0, 1.0, 10.0),
    "M8": (8.4, 10.0, 1.25, 13.0),
    "M10": (10.5, 12.0, 1.5, 16.0),
    "M12": (13.0, 14.5, 1.75, 18.0),
    "M16": (17.0, 18.5, 2.0, 24.0),
}


def nominal(size: str) -> float:
    return float(size[1:])


def clearance(size: str) -> tuple[float, float]:
    lo, hi, _, _ = FASTENERS[size]
    return lo, hi


def tap_drill(size: str) -> float:
    return round(nominal(size) - FASTENERS[size][2], 3)


def thread(size: str) -> str:
    return f"{size}x{FASTENERS[size][2]:g}"


def head(size: str) -> float:
    return FASTENERS[size][3]


def counterbore_depth(size: str) -> float:
    return nominal(size) + 0.4
