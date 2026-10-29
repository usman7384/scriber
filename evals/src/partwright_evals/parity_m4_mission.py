import json
import math
from pathlib import Path

import numpy as np

from partwright_context.aircraft import aircraft_design
from partwright_context.mission import ALL, Sizing, read_mission, size
from partwright_evals.parity import Demo, Evidence, Measured, Rig, evidence
from partwright_evals.parity_m4_aircraft import build, wing_checks
from partwright_geometry import Artifact
from partwright_ir import Design

FIXTURES = Path(__file__).parents[2] / "parity" / "m4" / "mission"


def linked_fields(design: Design, source: str) -> dict[str, set[str]]:
    prefix = f"{source}#"
    return {
        p.name: set(ref.removeprefix(prefix).split(",")) if (ref := p.provenance.ref or "").startswith(prefix) else set()
        for p in design.params
    }


def body_volume(rig: Rig, art: Artifact, half_width: float, stations: int = 9) -> float:
    ys = np.linspace(0.0, half_width, stations)
    areas = [_convex_area(outline) for outline in rig.geometry.sections(art.files["step"], [-y for y in ys])]
    return 2 * float(np.trapezoid(areas, ys))


def _convex_area(points: list[tuple[float, float, float]]) -> float:
    # symmetric NACA sections are convex, so sorting by angle about the centroid gives the outline
    xz = np.array([(x, z) for x, _, z in points])
    centre = xz.mean(0)
    ring = xz[np.argsort(np.arctan2(xz[:, 1] - centre[1], xz[:, 0] - centre[0]))]
    x, z = ring[:, 0], ring[:, 1]
    return float(abs(np.dot(x, np.roll(z, 1)) - np.dot(z, np.roll(x, 1))) / 2)


def _record(rig: Rig, sizing: Sizing, design: Design) -> None:
    out = {
        "config": sizing.config,
        "config_provenance": sizing.config_provenance.model_dump(),
        "estimates": {k: v.model_dump() for k, v in sizing.estimates.items()},
        "params": [p.model_dump() for p in design.params],
    }
    (rig.out / "sizing.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


def in_14(rig: Rig) -> Evidence:
    mission = read_mission(FIXTURES / "mission.yaml")
    sizing = size(mission)
    spec, design = sizing.spec, aircraft_design(sizing.spec)
    if not (spec.body and spec.inner_volume_mm3):
        raise ValueError(f"expected a blended wing body with a bay requirement, got {sizing.config}")
    _record(rig, sizing, design)
    art = build(rig, design, "uav")
    m, checks = wing_checks(rig, spec, art)
    links = linked_fields(design, mission.source)
    config_fields = set((sizing.config_provenance.ref or "").removeprefix(f"{mission.source}#").split(","))
    bay = body_volume(rig, art, spec.body.width.value / 2)
    extra: Measured = {
        "config": sizing.config,
        "params_linked": f"{sum(bool(v) and v <= set(ALL) for v in links.values())}/{len(links)}",
        "mtom_g": round(sizing.estimates["mtom_g"].value, 1),
        "battery_wh": round(sizing.estimates["battery_wh"].value, 2),
        "power_w": round(sizing.estimates["power_w"].value, 1),
        "body_bay_l": round(bay / 1e6, 3),
        "required_bay_l": round(spec.inner_volume_mm3.value / 1e6, 3),
    }
    checks += [
        all(v and v <= set(ALL) for v in links.values()),
        set(ALL) == {f for v in links.values() for f in v},
        config_fields <= set(ALL) and bool(config_fields),
        art.parts[0].bbox_size[1] <= mission.max_span_mm.value,
        math.isclose(spec.wing.span.value, 0.99 * mission.max_span_mm.value),
        bay >= spec.inner_volume_mm3.value,
    ]
    return evidence(
        "IN-14", {**m, **extra}, *checks, note="params and config cite mission fields; sweep, dihedral, fin sweep via the config"
    )


ROWS: dict[str, Demo] = {"IN-14": in_14}
