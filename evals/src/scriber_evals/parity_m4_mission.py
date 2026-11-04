import json
import math
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np

from scriber_context.aircraft import aircraft_design
from scriber_context.mission import ALL, Sizing, read_mission, size
from scriber_context.sizing import XmlSizing
from scriber_evals.parity import Demo, Evidence, Measured, Rig, evidence
from scriber_evals.parity_m4_aircraft import FIXTURES as AIRCRAFT
from scriber_evals.parity_m4_aircraft import build, wing_checks
from scriber_geometry import Artifact, BuildError, LocalGeometry, PartMetrics
from scriber_ir import Design, apply_params

FIXTURES = Path(__file__).parents[2] / "parity" / "m4" / "mission"
WORKERS = max(1, (os.cpu_count() or 2) // 2)
BUDGET_S = 600.0


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


def variants(rig: Rig, count: int = 1000, workers: int = WORKERS) -> Evidence:
    base = aircraft_design(XmlSizing().read(AIRCRAFT / "bwb.xml"))
    rng = np.random.default_rng(0)
    designs = [apply_params(base, {p.name: p.value * rng.uniform(0.9, 1.1) for p in base.params}) for _ in range(count)]
    start = time.monotonic()
    with ThreadPoolExecutor(workers) as pool:
        chunks = list(pool.map(partial(_measure_all, timeout=rig.config.geometry.timeout_s), [designs[i::workers] for i in range(workers)]))
    elapsed = time.monotonic() - start
    results = [r for chunk in chunks for r in chunk]
    good = [m for m, _ in results if m and m.solids == 1 and m.valid]
    seconds = [s for _, s in results]
    m: Measured = {
        "variants": count,
        "valid_single_solids": len(good),
        "distinct_volumes": len({round(g.volume, 3) for g in good}),
        "workers": workers,
        "elapsed_s": round(elapsed, 1),
        "rebuild_p50_s": round(float(np.median(seconds)), 3),
        "budget_s": round(BUDGET_S * count / 1000, 1),
    }
    checks = [len(good) == count, len({round(g.volume, 3) for g in good}) == count, elapsed <= BUDGET_S * count / 1000]
    return evidence(
        "PF-6", m, *checks, note="seeded +-10 % on every BWB param; compile and rebuild with validity and mass checks, no exports"
    )


def _measure_all(designs: list[Design], timeout: float) -> list[tuple[PartMetrics | None, float]]:
    geometry = LocalGeometry(timeout_s=timeout)
    try:
        return [_timed(geometry, d) for d in designs]
    finally:
        geometry.close()


def _timed(geometry: LocalGeometry, design: Design) -> tuple[PartMetrics | None, float]:
    start = time.monotonic()
    try:
        (part,) = geometry.measure(design)
    except BuildError:
        return None, time.monotonic() - start
    return part, time.monotonic() - start


def pf_2(rig: Rig) -> Evidence:
    timed = {"bwb_xml": _generate(rig, "bwb", lambda: aircraft_design(XmlSizing().read(AIRCRAFT / "bwb.xml")))}
    timed["mission_yaml"] = _generate(rig, "mission", lambda: aircraft_design(size(read_mission(FIXTURES / "mission.yaml")).spec))
    m: Measured = {f"{k}_s": round(v, 2) for k, v in timed.items()}
    return evidence(
        "PF-2", m, *(v < 300 for v in timed.values()), note="input file to exported, checked part; the aircraft template needs no model"
    )


def _generate(rig: Rig, name: str, design: Callable[[], Design]) -> float:
    start = time.monotonic()
    art = build(rig, design(), name)
    if not all(p.solids == 1 and p.valid for p in art.parts):
        raise ValueError(f"{name}: not one valid solid per part")
    return time.monotonic() - start


ROWS: dict[str, Demo] = {"IN-14": in_14, "PF-2": pf_2, "PF-6": variants}
