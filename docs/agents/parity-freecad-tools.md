# Parity: FreeCAD and PrusaSlicer checks

Closes **EX-4**, **EX-5** and **VM-9** when the integrator's live `scriber-parity EX-4 EX-5 VM-9` run passes with `SCRIBER_FREECAD` and `SCRIBER_PRUSASLICER` set (none of the three uses the model, so the offline tests and the live run measure the same thing). Tools, versions and licences: `docs/INTEROP.md#external-tools`.

## What landed

- `scriber_geometry.freecad`: `run_freecad` (subprocess runner; arguments and answer travel as JSON files), `step_in_freecad` (read a STEP, report solids, validity, volume, write it back) and `inspect_fcstd` (reopen an `.FCStd` in a fresh process, recompute everything, report each body's features, sketch DOF/redundant/conflicting counts per FreeCAD's solver, volume; then edit each named spreadsheet parameter and write a STEP per edit). The FreeCAD-side code is three `*.FCMacro` scripts next to the module.
- `scriber_geometry.fcstd`: `fcstd_plan` (IR → PartDesign plan, pure) and `export_fcstd` (writes it through FreeCAD). Sketch geometry and constraints come from `analyse_sketch` (the GE-3 sets), with each tangency and its coincidence merged into one endpoint tangency, because FreeCAD's edge-to-edge tangency is degenerate there. Sketch planes come from the kernel: the worker's new `frames` op runs the compiled model with `_ref` and `_extrude` wrapped and records every sketch plane (origin, axes, face side) and whether the profile's face normal opposes the plane (a clockwise outline extrudes the other way). Unmapped constructs raise `UnsupportedExportError`.
- `scriber_geometry.slicer.slice_stl`: PrusaSlicer `--info --export-gcode` with a throwaway datadir; exit code, manifold flag, layer count, G-code size, warning and error lines.
- `sketcher._slot` now pins the slot by an IR expression for its first arc centre instead of a plain position, so a slot follows edits of its centre, length, width and angle.
- Demos: EX-4 (`parity_m4_interop`) adds the FCStd half (bracket and IN-7 flange) and runs the AP-8 Onshape exporter on the recorded mock without the model; EX-5 (`parity_m5_platform`) round-trips the AP214 plate and the AP242 bracket through FreeCAD; VM-9 (`parity_m5_platform`, new) slices five reference parts and opens their STEP in FreeCAD. `scriber_evals.tools` reads the two variables.

## Measured (offline, FreeCAD 1.1.4, PrusaSlicer 2.9.6)

| Row | Result |
|---|---|
| EX-4 | bracket: `plate_sketch, Base plate (Pad), boss_sketch, Load boss (Pad), mount_holes_centres, Mounting holes (Pocket)`, sketches 20/3/12 constraints all 0 DOF, 0 redundant or conflicting, 17 expressions, volume drift 1.1e-16, 7/7 parameter edits reproduce our rebuild (volume, centre of mass, every hole). Flange: `disc, Body, hub, Hub, bore, Bore, bolts_centres, Bolt holes`, 0 DOF, 25 expressions, drift 2.0e-16, 7/7. Bundle half unchanged; Onshape export 10 features OK, no import call. 26/30 reference designs map; b07, b16 (counterbore), b10 (revolve), b27 (chamfer) raise. Pass |
| EX-5 | AP214 (`AUTOMOTIVE_DESIGN`, plate) and AP242 (bracket, `6061 aluminium`): FreeCAD reads 1 valid solid each, volume drift 1.5e-16 / 1.0e-14; FreeCAD's re-export reads back in our worker as 1 valid solid, volume drift 1.5e-16 / 0, bbox drift 0. Pass |
| VM-9 | b05 shaft collar 33 layers, b11 lightened disc 50, b17 cup 133, b21 gear blank 60, b27 control knob 50: all exit 0, manifold, 0 warnings, 0 errors, G-code 0.7–3.6 MB (deleted after counting); FreeCAD 1 valid solid each, volume drift ≤ 4.4e-14 except b05 at 5.1e-6 (FreeCAD heals the cross-drilled bore; our worker reads FreeCAD's re-export with the same 5.5e-6). Pass |

`test_fcstd.py` also rebuilds a design with every mapped construct (rounded rect, slot with a parameter angle, filleted path, clockwise polygon, polygon on XZ, rect on offset YZ, datum plane rotated 10°, two-sided pad, symmetric pad and pocket, through-all pocket from a face and from a datum, blind pocket from a face, blind holes from the bottom face, polar and grid holes, sketches on start, end and named faces): volume drift below 1e-9, and four parameter edits match our rebuild.

## Run

```
export SCRIBER_FREECAD=.../FreeCAD_1.1.4-Windows-x86_64-py311/bin/freecadcmd.exe
export SCRIBER_PRUSASLICER=.../PrusaSlicer-2.9.6/prusa-slicer-console.exe
uv run pytest services/geometry/tests/test_fcstd.py evals/tests/test_parity_m4_interop.py evals/tests/test_parity_m5_platform.py
uv run scriber-parity EX-4 EX-5 VM-9
```

Without the variables the tool-backed tests skip and the demos report the rows open with `not configured: ... is unset`.

## Gaps

- FCStd: no revolve, pattern, fillet, chamfer, shell, loft, airfoil, counterbore or countersink mapping; no assemblies. Sketches are unattached and placed by expression; only sketches on the start or end face of a blind extrude follow that extrude. Details in `docs/INTEROP.md`.
- The Onshape half of EX-4 is the feature-API export of AP-8, not FeatureScript source.
- VM-9 slices with PrusaSlicer's built-in defaults (no printer profile, no orientation choice, no support check beyond what the defaults do). WP-14's slicer check is not wired to these demos.
- FreeCAD and our worker share OCCT; EX-5 says nothing about how a different kernel reads the file.
