# Parity M4: aircraft from a mission definition

Branch `feat/m4-mission`. Closes offline, with the real geometry worker: **IN-14**, **PF-2**, **PF-6**. None of them uses the model, so the offline test and the live `partwright-parity` run measure the same thing (PF-6 offline runs a 16-variant slice; the 1,000-variant timing is the live run).

## What landed

- **Context** `partwright_context.mission`: `read_mission(path)` reads `mission.yaml` (`payload.mass`, `endurance`, `constraints.max_span`, any pint unit) with each field's YAML key as provenance; `size(mission)` is a pure first-order sizing that returns the configuration, the estimates (MTOM, battery Wh, cruise power, aspect ratio) and an `AircraftSpec` for `aircraft_design`. Every value has `Provenance(source="rule", ref="mission.yaml#<fields>", quote=<formula>)`.
- **Geometry** `LocalGeometry.measure(design)`: compile, rebuild and return part metrics without writing STEP/STL/GLB.
- **Evals** `partwright_evals.parity_m4_mission.ROWS`: IN-14, PF-2, PF-6. Fixture `evals/parity/m4/mission/mission.yaml`.

## Sizing (first order, all constants in `mission.py`)

| Step | Formula | Assumptions |
|---|---|---|
| Cruise speed | V = sqrt(2 (W/S) / (rho CL)) | W/S 50 N/m², CL 0.5, ISA sea level |
| Battery mass share | k = g V t / (L/D · eta · e) | L/D 10, eta 0.5, e = 120 Wh/kg usable (LiPo 150 Wh/kg, 80 %) |
| Take-off mass | m = payload / (1 − empty share − k) | empty share 0.45; fails if the budget does not close |
| Energy, power | E = k m e, P = m g V / (L/D · eta) | |
| Wing | b = 0.99 b_max, S = m g / (W/S), c_root = 2S / (b (1 + λ)), c_tip = λ c_root | λ 0.45, NACA 0012 |
| Bay | (payload / 1 g/cm³ + E / 300 Wh/l) / 0.5 packing | |
| Configuration | blended wing body if the bay exceeds the wing root over the body width (0.685 t c² · w), else flying wing | body width 0.15 b |
| Body chord | 1.1 · bay = w · 0.685 (t_body c_body² + t_wing c_root²) / 2 | NACA 0018; 1.1 covers the loft sagging below the linear blend |
| Washout | Panknin: twist = CL σ / (1.4e-5 AR^1.43 φ¼) (symmetric sections, Cm0 = 0) | σ = 0.05 static margin, LE sweep 25° |
| Dihedral | 5° − sweep / 10 (each 10° of sweep adds about 1° of effective dihedral) | |
| Fins | V_v = 2 S_fin l / (S b) = 0.02, fin root = wing tip chord, taper 0.6, swept like the wing | NACA 0010 |

Sources: wing loading, level-flight power and the mass fractions are the usual conceptual-design relations (Raymer, *Aircraft Design: A Conceptual Approach*), with the battery energy balance E = P t; washout is W. Panknin's twist formula ("Flying Wings", MARCS symposium 1989); the dihedral-from-sweep line is a rule of thumb; 0.685 is the integral of the NACA 4-digit thickness distribution.

Sweep, dihedral and fin sweep are configuration defaults: they reach the mission only through the configuration decision (which uses all three fields). Everything else is computed from the fields it cites.

## Measured (offline run)

| Row | Result |
|---|---|
| IN-14 | blended wing body (bay 1.06 l > wing root 0.82 l); MTOM 1040.9 g, battery 8.7 Wh, cruise 26.1 W, AR 6.91; 11/11 params cite mission fields; built span 1188.0 ≤ 1200, chords 237.12/106.70, sweep 25.001°, dihedral 2.500°, washout 5.142°, NACA 0012 deviation 0.0064 % chord; body bay 1.143 l ≥ 1.058 l required |
| PF-2 | bwb.xml → exported part 3.51 s; mission.yaml → exported part 3.89 s (one part each, < 300 s) |
| PF-6 | 1,000 seeded variants (±10 % on all 11 BWB params): 1,000 valid single solids, 1,000 distinct volumes, 489.2 s on 8 worker processes (budget 600 s), per-variant p50 3.70 s under that load; the laptop GPU was training at the time |

## Run

```
uv run pytest services/context/tests/test_mission.py evals/tests/test_parity_m4_mission.py
uv run partwright-parity IN-14 PF-2 PF-6   # after the module is registered in parity.registry()
```

## Gaps

- IN-14: the agent's `generate` does not route a mission file to the sizing step yet; the demo calls it directly. No natural-language mission brief.
- The sizing is first order with fixed assumptions (no drag polar, propeller or motor model, no CG estimate); it is explainable, not optimised.
- PF-6 relies on parallel workers; one worker rebuilds a BWB variant in about 1.0–1.5 s, nearly all of it OCCT booleans (winglet fuse and two mirror fuses).
- PF-2: one part per BWB fixture; the time is the deterministic template plus build and export, without the model.
