import math
from pathlib import Path
from typing import Any, Literal

import yaml

from partwright_context.models import Frozen
from partwright_context.quantities import to_unit
from partwright_context.sizing import AircraftSpec, Body, Sourced, Tail, Wing
from partwright_ir import Provenance

G = 9.81
RHO = 1.225  # ISA sea level, kg/m3
CL_CRUISE = 0.5
WING_LOADING = 50.0  # N/m2; small electric flying wings fly at 30-60
LIFT_TO_DRAG = 10.0
EFFICIENCY = 0.5  # motor x ESC x propeller
BATTERY_WH_PER_KG = 120.0  # LiPo at 150 Wh/kg, 80 % usable
BATTERY_WH_PER_L = 300.0
EMPTY_FRACTION = 0.45  # airframe, motor and avionics share of take-off mass
PAYLOAD_G_PER_CM3 = 1.0
PACKING = 0.5  # share of the bay that boxes can fill
SPAN_MARGIN = 0.99
TAPER = 0.45
BODY_SPAN_SHARE = 0.15
SWEEP = 25.0  # leading-edge sweep of a tailless wing
STATIC_MARGIN = 0.05
FIN_VOLUME = 0.02
FIN_TAPER = 0.6
SECTION_AREA = 0.685  # NACA 00xx section area / (thickness x chord)
LOFT_MARGIN = 1.1  # the smooth body loft sags below the linear blend of its end sections
WING, BODY, FIN = "0012", "0018", "0010"
PAYLOAD, ENDURANCE, MAX_SPAN = "payload.mass", "endurance", "constraints.max_span"
ALL = (PAYLOAD, ENDURANCE, MAX_SPAN)
Config = Literal["blended_wing_body", "flying_wing"]


class Mission(Frozen):
    name: str
    source: str
    payload_g: Sourced
    endurance_s: Sourced
    max_span_mm: Sourced


class Sizing(Frozen):
    config: Config
    config_provenance: Provenance
    estimates: dict[str, Sourced]
    spec: AircraftSpec


def read_mission(path: Path) -> Mission:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("mission"), dict):
        raise ValueError(f"{path.name}: expected a top-level 'mission' mapping")
    mission = data["mission"]
    return Mission(
        name=str(mission.get("name", path.stem)),
        source=path.name,
        payload_g=_field(path.name, mission, PAYLOAD, "g"),
        endurance_s=_field(path.name, mission, ENDURANCE, "s"),
        max_span_mm=_field(path.name, mission, MAX_SPAN, "mm"),
    )


def _field(source: str, mission: dict[str, Any], key: str, unit: str) -> Sourced:
    node: Any = mission
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ValueError(f"{source}: missing mission.{key}")
        node = node[part]
    try:
        value = to_unit(str(node), unit)
    except ValueError as e:
        raise ValueError(f"{source}: mission.{key} {e}") from e
    if value <= 0:
        raise ValueError(f"{source}: mission.{key} must be positive, got {node!r}")
    return Sourced(value=value, provenance=Provenance(source="document", ref=f"{source}#{key}", quote=f"{key}: {node}"))


def size(m: Mission) -> Sizing:
    def rule(value: float, fields: tuple[str, ...], formula: str) -> Sourced:
        return Sourced(value=value, provenance=Provenance(source="rule", ref=f"{m.source}#{','.join(fields)}", quote=formula))

    mtom, energy, power = _budget(m)
    span = SPAN_MARGIN * m.max_span_mm.value
    area = mtom / 1000 * G / WING_LOADING * 1e6
    root = 2 * area / span / (1 + TAPER)
    tip, aspect, width = TAPER * root, span**2 / area, BODY_SPAN_SHARE * span
    bay = (m.payload_g.value / PAYLOAD_G_PER_CM3 * 1e3 + energy / BATTERY_WH_PER_L * 1e6) / PACKING
    wing_bay = width * SECTION_AREA * _thickness(WING) * root**2
    bwb = bay > wing_bay
    config: Config = "blended_wing_body" if bwb else "flying_wing"
    body_chord = _body_chord(bay, width, root) if bwb else root
    panel = (span - width) / 2 if bwb else span / 2
    arm = body_chord - root + panel * math.tan(math.radians(SWEEP)) + tip / 4 - body_chord / 4
    sized = "S = m g / (W/S), m = payload / (1 - empty share - battery share)"
    spec = AircraftSpec(
        name=m.name,
        source=m.source,
        wing=Wing(
            naca=WING,
            span=rule(span, (MAX_SPAN,), f"b = {SPAN_MARGIN} x max span"),
            root_chord=rule(root, ALL, f"{sized}; c_root = 2 S / (b (1 + taper {TAPER}))"),
            tip_chord=rule(tip, ALL, f"{sized}; c_tip = taper {TAPER} x c_root"),
            sweep=rule(SWEEP, ALL, f"{config} default: leading-edge sweep {SWEEP} deg"),
            dihedral=rule(max(5 - SWEEP / 10, 0), ALL, f"{config} default: dihedral = 5 deg - sweep / 10"),
            twist=rule(_washout(aspect, root, tip, panel), ALL, f"Panknin washout = CL sigma / (1.4e-5 AR^1.43 phi_c/4), AR {aspect:.2f}"),
        ),
        body=Body(
            naca=BODY,
            chord=rule(body_chord, ALL, f"{LOFT_MARGIN} x bay = width x {SECTION_AREA} (t_body c_body^2 + t_wing c_root^2) / 2"),
            width=rule(width, (MAX_SPAN,), f"width = {BODY_SPAN_SHARE} x b"),
        )
        if bwb
        else None,
        tail=Tail(
            naca=FIN,
            span=rule(_fin_height(area, span, arm, tip), ALL, f"fin volume {FIN_VOLUME} = 2 S_fin l_fin / (S b)"),
            tip_chord=rule(FIN_TAPER * tip, ALL, f"fin tip = {FIN_TAPER} x wing tip chord"),
            sweep=rule(SWEEP, ALL, f"{config} default: fins swept like the wing"),
        ),
        inner_volume_mm3=rule(bay, (PAYLOAD, ENDURANCE), "bay = (payload / density + battery Wh / Wh per l) / packing"),
    )
    estimates = {
        "mtom_g": rule(mtom, (PAYLOAD, ENDURANCE), sized),
        "battery_wh": rule(energy, (PAYLOAD, ENDURANCE), "E = m g V t / (L/D eta)"),
        "power_w": rule(power, (PAYLOAD, ENDURANCE), "P = m g V / (L/D eta)"),
        "aspect_ratio": rule(aspect, ALL, "AR = b^2 / S"),
    }
    why = Provenance(source="rule", ref=f"{m.source}#{','.join(ALL)}", quote=f"bay {bay / 1e6:.2f} l vs wing root {wing_bay / 1e6:.2f} l")
    return Sizing(config=config, config_provenance=why, estimates=estimates, spec=spec)


def _budget(m: Mission) -> tuple[float, float, float]:
    speed = math.sqrt(2 * WING_LOADING / (RHO * CL_CRUISE))
    battery_share = G * speed * m.endurance_s.value / (LIFT_TO_DRAG * EFFICIENCY * BATTERY_WH_PER_KG * 3600)
    if (left := 1 - EMPTY_FRACTION - battery_share) <= 0.05:
        raise ValueError(f"{m.source}: {m.endurance_s.value / 60:g} min needs {battery_share:.0%} battery; the mass budget does not close")
    mtom = m.payload_g.value / left
    return mtom, battery_share * mtom / 1000 * BATTERY_WH_PER_KG, mtom / 1000 * G * speed / (LIFT_TO_DRAG * EFFICIENCY)


def _thickness(naca: str) -> float:
    return int(naca[2:]) / 100


def _body_chord(bay: float, width: float, root: float) -> float:
    squared = (2 * LOFT_MARGIN * bay / (width * SECTION_AREA) - _thickness(WING) * root**2) / _thickness(BODY)
    return max(math.sqrt(max(squared, 0.0)), root)


def _washout(aspect: float, root: float, tip: float, panel: float) -> float:
    quarter_sweep = math.degrees(math.atan(math.tan(math.radians(SWEEP)) - (root - tip) / (4 * panel)))
    return CL_CRUISE * STATIC_MARGIN / (1.4e-5 * math.pow(aspect, 1.43) * quarter_sweep)


def _fin_height(area: float, span: float, arm: float, tip: float) -> float:
    fin_area = FIN_VOLUME * area * span / (2 * arm)
    return 2 * fin_area / (tip * (1 + FIN_TAPER))
