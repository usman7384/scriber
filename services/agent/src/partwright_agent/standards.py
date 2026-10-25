import re

# EN 1092-1 PN16 flat flanges: DN -> (outer diameter, bolt circle, bolt count, hole diameter, bolt)
EN1092_PN16 = {
    15: (95, 65, 4, 14, "M12"),
    20: (105, 75, 4, 14, "M12"),
    25: (115, 85, 4, 14, "M12"),
    32: (140, 100, 4, 18, "M16"),
    40: (150, 110, 4, 18, "M16"),
    50: (165, 125, 4, 18, "M16"),
    80: (200, 160, 8, 18, "M16"),
    100: (220, 180, 8, 18, "M16"),
}

# NEMA stepper frames: size -> (faceplate square, hole pattern square, pilot diameter, screw)
NEMA = {
    8: (20.0, 16.0, 15.0, "M2"),
    11: (28.0, 23.0, 22.0, "M2.5"),
    14: (35.0, 26.0, 22.0, "M3"),
    17: (42.3, 31.0, 22.0, "M3"),
    23: (56.4, 47.14, 38.1, "M5"),
}

# B-type aluminium extrusion series: series -> (slot opening, T-nut screw)
EXTRUSION = {20: (6.0, "M5"), 30: (8.0, "M6"), 40: (8.0, "M8")}


def reference_data(text: str) -> list[str]:
    return [*_flanges(text), *_nema(text), *_extrusions(text)]


def _flanges(text: str) -> list[str]:
    out = []
    for dn in sorted({int(m) for m in re.findall(r"\bDN\s?(\d+)", text, re.IGNORECASE)}):
        if dn in EN1092_PN16:
            od, pcd, n, hole, bolt = EN1092_PN16[dn]
            out.append(f"EN 1092-1 PN16 DN{dn} flange: outer diameter {od} mm, bolt circle {pcd} mm, {n} holes of {hole} mm for {bolt}.")
    return out


def _nema(text: str) -> list[str]:
    out = []
    for size in sorted({int(m) for m in re.findall(r"\bNEMA\s?(\d+)", text, re.IGNORECASE)}):
        if size in NEMA:
            face, square, pilot, screw = NEMA[size]
            out.append(
                f"NEMA {size} motor: faceplate {face} mm square, mounting holes for {screw} on a {square} mm square "
                f"(hole centres at +-{square / 2:g} mm from the shaft); the motor's centring pilot needs a {pilot} mm hole."
            )
    return out


def _extrusions(text: str) -> list[str]:
    if not re.search(r"extrusion|profile|v-slot|t-slot", text, re.IGNORECASE):
        return []
    out = []
    for series, length in sorted({(int(a), int(b)) for a, b in re.findall(r"\b(20|30|40)(20|40|60|80)\b", text)}):
        slot, screw = EXTRUSION[series]
        out.append(
            f"{series}{length} aluminium extrusion: {series} x {length} mm, slot centres every {series} mm, "
            f"slot opening {slot} mm, fastened with {screw} T-nuts."
        )
    return out


# ISO 273 fine to coarse clearance range by thread
ISO273_RANGE = {
    "M2": (2.2, 2.6),
    "M2.5": (2.7, 3.1),
    "M3": (3.2, 3.6),
    "M4": (4.3, 4.8),
    "M5": (5.3, 5.8),
    "M6": (6.4, 7.0),
    "M8": (8.4, 10.0),
    "M10": (10.5, 12.0),
    "M12": (13.0, 14.5),
}
