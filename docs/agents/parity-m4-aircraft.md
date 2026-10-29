# Parity M4: aircraft from sizing XML

Branch `feat/m4-aircraft`. Closes (offline, with the real geometry worker): **IN-11, CD-6, GE-4, DP-9, DP-10**. None of these rows uses the model, so the offline test and the live `partwright-parity` run measure the same thing.

## What landed

- **IR** (additive): `airfoil_section` feature (plane, NACA 4-digit code, chord, leading-edge position in the plane, twist about the leading edge, positive nose-up) and `loft` feature (ordered section ids, `ruled`). Lofts can be patterned (mirror). `Part.sketches` may be empty. The NACA generator `partwright_ir.airfoil.naca4` is a pure function; the compiler embeds its source in model code only when a design has airfoil sections, so every existing design compiles byte-identically (`evals/tests/test_compile_golden.py`).
- **Geometry**: `LocalGeometry.sections(step, ys)` cuts the built STEP with planes `y = const` and returns the outline points.
- **Context**: `SizingAdapter` protocol (`read(path) -> AircraftSpec`), reference `XmlSizing` adapter, and `aircraft_design(spec)`, a deterministic template that emits typed IR (no LLM). Every parameter carries the XML element as provenance. Wing only: `root_airfoil`, `tip_airfoil`, `main_wing`, `full_aircraft`. With `<body>` and `<tail>`: a blended wing body with `mid_airfoil` at the body edge and wing-tip fins (`winglet_*`, `winglet_assembly`).
- **Evals**: `partwright_evals.parity_m4_aircraft.ROWS`. Sections are compared with NACA by a best-fit similarity transform (ICP); chord, leading edge and incidence come from the fit, deviation is the worst point-to-curve residual in % chord.

XML format (units on every value; mm/cm/m, deg/rad, l/mm3/cm3/dm3/m3): see `evals/parity/m4/aircraft/bwb.xml`. Sweep and dihedral are leading-edge angles of the outer wing; twist is washout at the tip.

## Measured (offline run)

| Row | Result |
|---|---|
| IN-11 | span 1000.0, chords 250.036 / 120.017, sweep 20.002°, dihedral 5.000°, twist 2.000°, airfoil deviation 0.015 % chord |
| CD-6 | span 1000 → 1100 in the XML: only `wing_span` changes, new span 1100.0, v1 STEP still 1000.0 |
| GE-4 | BWB tree root/mid/tip_airfoil, main_wing, winglet_root/tip_airfoil, winglet, winglet_assembly, full_aircraft; same order in the compiled model; one valid solid |
| DP-9 | as IN-11 on the BWB built from the five given params; bbox 46.6 / 100.0 / 18.4 cm |
| DP-10 | as IN-11 plus body NACA 0018 chord 420.032, deviation 0.0096 %; enclosed volume 2.038 l ≥ 1.8 l |

## Run

```
uv run pytest evals/tests/test_parity_m4_aircraft.py evals/tests/test_compile_golden.py
uv run partwright-parity IN-11 CD-6 GE-4 DP-9 DP-10   # after the module is registered in parity.registry()
```

## Gaps

- CD-6 re-run is explicit (read XML again, rebuild); no watcher or API trigger yet (CD-1, AP-9).
- The agent's `generate` does not route a sizing XML to the adapter yet; the adapter is called directly.
- DP-10: control surfaces and performance values (static margin, CoG, MTOM, battery, motor, propeller) are not modelled; the adapter ignores them. The volume is checked, not sized for.
- DP-9: the reference bbox labels (112.8 / 16.4 / 36.4 cm) come from geometry we cannot see and are not reproduced.
- PF-6 not attempted: one BWB rebuild with exports takes about 3–4 s, so 1,000 variants would take about an hour.
- The IR JSON schema changed (two new feature kinds, `sketches` no longer `minItems: 1`), so constrained decoding now allows them; prompts are unchanged.
