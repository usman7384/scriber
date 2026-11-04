import re
from functools import cache

from pint import PintError, UnitRegistry

NUM = r"\d+(?:[.,]\d+)?"
TIMES = chr(0xD7)
MINUS = chr(0x2212)
PINT = {
    "mm": "millimeter",
    "cm": "centimeter",
    "µm": "micrometer",
    "μm": "micrometer",
    "um": "micrometer",
    "m": "meter",
    "in": "inch",
    "inch": "inch",
    "inches": "inch",
    '"': "inch",
    "ft": "foot",
    "deg": "degree",
    "°": "degree",
    "rad": "radian",
    "N": "newton",
    "kN": "kilonewton",
    "Nm": "newton * meter",
    "N·m": "newton * meter",
    "kg": "kilogram",
    "g": "gram",
    "MPa": "megapascal",
    "GPa": "gigapascal",
}
UNIT = "(?:" + "|".join(re.escape(u) for u in sorted(PINT, key=len, reverse=True)) + r")(?![A-Za-z])"
QUANTITY = re.compile(rf"(?<![\w.])(?P<v>{NUM})\s*(?P<u>{UNIT})")
TARGETS = (("millimeter", "mm"), ("degree", "deg"), ("newton", "N"), ("kilogram", "kg"), ("megapascal", "MPa"), ("newton * meter", "N*m"))


@cache
def _registry() -> UnitRegistry:
    return UnitRegistry()


def number(text: str) -> float:
    return float(text.replace(",", "."))


def normalise(value: float, unit: str) -> tuple[float, str]:
    quantity = _registry().Quantity(value, PINT[unit])
    for name, short in TARGETS:
        if quantity.is_compatible_with(name):
            return round(float(quantity.to(name).magnitude), 6), short
    raise ValueError(f"no target unit for {unit}")


def to_unit(text: str, unit: str) -> float:
    try:
        return float(_registry().Quantity(text).to(unit).magnitude)
    except PintError as e:
        raise ValueError(f"{text!r} is not a quantity in {unit}: {e}") from e


def quantities(text: str) -> list[tuple[float, str]]:
    return [normalise(number(m["v"]), m["u"]) for m in QUANTITY.finditer(text)]
