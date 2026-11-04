import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Protocol

from scriber_context.models import Frozen
from scriber_context.quantities import PINT, normalise, number
from scriber_ir import Provenance

NACA = re.compile(r"^\s*(?:NACA\s*)?(\d{4})\s*$", re.IGNORECASE)
VALUE = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)\s*(\S+)?\s*$")
VOLUME_MM3 = {"mm3": 1.0, "cm3": 1e3, "l": 1e6, "dm3": 1e6, "m3": 1e9}


class Sourced(Frozen):
    value: float
    provenance: Provenance


class Wing(Frozen):
    naca: str
    span: Sourced
    root_chord: Sourced
    tip_chord: Sourced
    sweep: Sourced
    dihedral: Sourced
    twist: Sourced


class Body(Frozen):
    naca: str
    chord: Sourced
    width: Sourced


class Tail(Frozen):
    naca: str
    span: Sourced
    tip_chord: Sourced
    sweep: Sourced


class AircraftSpec(Frozen):
    name: str
    source: str
    wing: Wing
    body: Body | None = None
    tail: Tail | None = None
    inner_volume_mm3: Sourced | None = None


class SizingAdapter(Protocol):
    def read(self, path: Path) -> AircraftSpec: ...


class XmlSizing:
    def read(self, path: Path) -> AircraftSpec:
        root = ET.parse(path).getroot()
        if root.tag != "aircraft":
            raise ValueError(f"{path.name}: expected an <aircraft> root, got <{root.tag}>")
        r = _Reader(path.name, root)
        wing = Wing(
            naca=r.naca("wing/airfoil"),
            span=r.length("wing/span"),
            root_chord=r.length("wing/root_chord"),
            tip_chord=r.length("wing/tip_chord"),
            sweep=r.angle("wing/sweep"),
            dihedral=r.angle("wing/dihedral"),
            twist=r.angle("wing/twist"),
        )
        body = Body(naca=r.naca("body/airfoil"), chord=r.length("body/chord"), width=r.length("body/width")) if r.has("body") else None
        tail = (
            Tail(naca=r.naca("tail/airfoil"), span=r.length("tail/span"), tip_chord=r.length("tail/tip_chord"), sweep=r.angle("tail/sweep"))
            if r.has("tail")
            else None
        )
        volume = r.volume("requirements/inner_volume") if r.has("requirements/inner_volume") else None
        return AircraftSpec(name=root.get("name", path.stem), source=path.name, wing=wing, body=body, tail=tail, inner_volume_mm3=volume)


class _Reader:
    def __init__(self, source: str, root: ET.Element) -> None:
        self.source, self.root = source, root

    def has(self, path: str) -> bool:
        return self.root.find(path) is not None

    def naca(self, path: str) -> str:
        text = self._element(path).text or ""
        if not (match := NACA.match(text)):
            raise ValueError(f"{self.source}: <{path}> must be a NACA 4-digit airfoil such as 'NACA 2412', got {text.strip()!r}")
        return match.group(1)

    def length(self, path: str) -> Sourced:
        return self.quantity(path, "mm")

    def angle(self, path: str) -> Sourced:
        return self.quantity(path, "deg")

    def quantity(self, path: str, target: str) -> Sourced:
        value, unit, provenance = self._value(path)
        converted, kind = normalise(value, unit) if unit in PINT else (value, unit)
        if kind != target:
            raise ValueError(f"{self.source}: <{path}> is in {unit}; expected a {target}-compatible unit")
        return Sourced(value=converted, provenance=provenance)

    def volume(self, path: str) -> Sourced:
        value, unit, provenance = self._value(path)
        if unit not in VOLUME_MM3:
            raise ValueError(f"{self.source}: <{path}> unit {unit!r} is not one of {sorted(VOLUME_MM3)}")
        return Sourced(value=value * VOLUME_MM3[unit], provenance=provenance)

    def _value(self, path: str) -> tuple[float, str, Provenance]:
        element = self._element(path)
        text = (element.text or "").strip()
        match = VALUE.match(text)
        unit = element.get("unit") or (match.group(2) if match else None)
        if not match or not unit:
            raise ValueError(f"{self.source}: <{path}> needs a number with a unit, got {text!r}")
        quote = ET.tostring(element, encoding="unicode").strip()
        return number(match.group(1)), unit, Provenance(source="document", ref=f"{self.source}#{path}", quote=quote)

    def _element(self, path: str) -> ET.Element:
        element = self.root.find(path)
        if element is None:
            raise ValueError(f"{self.source}: missing <{path}>")
        return element
