# Interoperability

What goes in and out of Scriber, and what does not. Everything here runs offline on open code (OCCT through build123d). FreeCAD and PrusaSlicer are optional external tools for the checks below; see [External tools](#external-tools).

## Supported

| Path | Direction | What survives | Test |
|---|---|---|---|
| STEP AP242 (`.step`, `.stp`) | in | body names and assembly paths, named faces, materials and densities, solids | `test_parity_m4_interop` IN-10, `test_step_meta.py` |
| STEP AP242 | out | body names, named face groups (`mount_face`, `load_face`, ...), material and density per part. Written only when the design has face groups or materials; otherwise build123d's AP214 export is used unchanged | GE-12 |
| STL, OBJ | in | mesh descriptor only (bbox, area, watertight volume) | `test_import.py` |
| STL, glTF (`.glb`) | out | tessellation for viewing and printing | EX-2, EX-3 |
| IR bundle (`.zip`) | out and in | `design.json` (the IR), `model.py`, `params.json`, `features.json` (ordered tree with dependencies), `sketches.json` (geometry, constraints and DOF per sketch), `model.step`. Reopening checks the hash, that `model.py` replays from `design.json`, and recounts every sketch's DOF | EX-4 (bundle half), GE-3 |
| FreeCAD `.FCStd` | out | one PartDesign Body per part, features in IR order and labelled with the IR names: a Sketch per extrude and per hole feature (geometry plus our derived constraint set, fully constrained per FreeCAD's solver), then a Pad (extrude add) or Pocket (extrude cut, holes). A `Parameters` spreadsheet holds every IR parameter; constraint values, pad/pocket lengths, base-plane offsets, hole centres (points, grid, polar) and sketches on the start/end face of a blind extrude are expressions over it, so editing a cell rebuilds the same part our kernel builds | EX-4, `test_fcstd.py` (needs FreeCAD) |
| STEP AP214 and AP242 | out, opened by FreeCAD | one valid solid with our volume; FreeCAD's re-export reads back with drift below 1e-6 | EX-5 (needs FreeCAD) |
| STL | out, sliced by PrusaSlicer | manifold, slices without errors, layer count | VM-9 (needs PrusaSlicer and FreeCAD) |
| Onshape part studio | in | feature list (id, name, type, suppression), part names and materials, a STEP translation; sketches on the default planes (lines, circles) and solid extrudes (new, add, remove; blind or through all) become IR | IN-10, against a recorded mock |
| Onshape part studio | out | native features, no STEP: every parameter as a variable (`assignVariable`), sketches on Top/Front/Right or offset construction planes (lines, circles), extrudes (new, add, remove, intersect; blind, symmetric, through all, up to next) and holes (simple, counterbore, countersink at the IR hole centres). Features carry the IR names (sketch ids, feature names, parameter names); depths, diameters and offsets that are a parameter or a sum of parameters stay linked as `#name` expressions | AP-8, against a recorded mock |

## Export to other CAD systems

CATIA, NX, SolidWorks and Creo all import STEP, so STEP is the export path to them: AP242 (product structure, part names, named face groups, materials) when the design has face groups or materials, AP214 otherwise. Download it from `GET /models/{id}/export?fmt=step` or the IR bundle.

- Tested: an OCCT round trip (EX-5): write the STEP, read it back, compare volume and bounding box (drift below 1e-6), solid count, validity, schema and material.
- Tested: FreeCAD 1.1.4 opens both flavours (EX-5): the AP214 default export (plate) and the AP242 face-group/material export (load bracket) each read as 1 valid solid with volume drift about 1e-14; FreeCAD writes them back to STEP and our geometry worker reads that file as 1 valid solid with volume and bounding-box drift below 1e-6.
- Not tested: none of the proprietary systems are available. FreeCAD shares OCCT with us, so it is a check of the file, not of another kernel.
- Gaps: no PMI (GD&T, dimensions, tolerances), no feature history in STEP (other systems get a dumb solid; FreeCAD gets history through `.FCStd`), no proprietary native formats, no assembly constraints (mates travel only in our IR bundle), and colours are not written.

## Not yet built

- **FreeCAD `.FCStd` gaps** (`export_fcstd` in `scriber_geometry.fcstd`): revolves, patterns, fillets, chamfers, shells, airfoil sections, lofts, intersect/up-to-next/tapered extrudes, through-all pads, counterbore and countersink holes, blind holes with a 118° drill point, profiles mixing clockwise and counter-clockwise outlines and designs with an assembly raise `UnsupportedExportError` (26 of the 30 M5 reference designs map; b07 and b16 have counterbores, b10 is a revolve, b27 has a chamfer). Sketches are placed by their plane, not attached to faces: a sketch on a face is linked by expression only to the start or end face of a blind extrude on a parallel plane; on any other face or datum it sits at the face's position as a number, so an edit that moves that face leaves the sketch behind. IR expressions with `min`, `max`, `abs`, `round`, `%`, `//` or `**` stay numbers. Spreadsheet aliases of four characters or fewer get a trailing `_` (`t` → `t_`), because FreeCAD rejects unit symbols and constants as aliases.
- **FeatureScript export**: no `.fs` source is written. The Onshape half of EX-4 is the native feature export above (AP-8), tested against the recorded mock.
- **Onshape export gaps** (`export_onshape` in `scriber_geometry.onshape_export`): only the `OnshapeApi` protocol and a recorded replay, no HTTP client; the recorded session (`evals/parity/m5/onshape/`) was written from the public docs as we read them, not captured from a live account, so feature and parameter ids are unverified against a real server. Sketch geometry is sent as numbers with no sketch constraints. Fillets, chamfers, shells, patterns, revolves, lofts, rounded rectangles, slots, paths, subtracted profiles, two-sided extrudes, tapers and sketches on faces or datums raise `UnsupportedExportError` instead of being dropped. Holes drill against the sketch normal (Onshape's convention), so a hole plane must be the entry face; tapped holes go out as their tap drill; blind holes keep Onshape's default tip. Each IR part gets its own part studio, next to the document's default empty one.
- **Onshape import gaps**: sketch constraints and dimensions are not read (we derive our own, see GE-3), arcs and splines are not mapped, `booleanScope` is ignored (add and remove act on the latest new body), the STEP translation is not polled, and no HTTP client exists: only the `OnshapeApi` protocol and the recorded replay. The recorded responses follow the public API docs ([features](https://onshape-public.github.io/docs/api-adv/featureaccess/), [translations](https://onshape-public.github.io/docs/api-adv/translation/)) as we read them; they were not captured from a live account.
- **PMI** (GD&T, dimensions) in STEP AP242: not written or read.

## External tools

Both are optional, run as subprocesses only (never imported into our processes), and are found through environment variables; tests that need them are skipped when the variable is unset, and the parity demos report the row as open.

| Tool | Version | Licence | Variable | Used for | Download |
|---|---|---|---|---|---|
| FreeCAD (`freecadcmd`) | 1.1.4 | LGPL-2.1+ | `SCRIBER_FREECAD` (path to `freecadcmd`) | `.FCStd` export and reopening (EX-4), STEP round trip (EX-5, VM-9) | <https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.4> |
| PrusaSlicer CLI (`prusa-slicer-console`) | 2.9.6 | AGPL-3.0 | `SCRIBER_PRUSASLICER` | slicing exported STL (VM-9) | <https://github.com/prusa3d/PrusaSlicer/releases/tag/version_2.9.6> |

`scriber_geometry.freecad.run_freecad` passes its arguments in a JSON file to a small script next to the module (`*.FCMacro`) and reads the answer from a result file, because `freecadcmd` interleaves its progress output with anything the script prints. Our Python variables (`PYTHONPATH`, `VIRTUAL_ENV`, ...) are removed from FreeCAD's environment. The API exposes both (`GET /models/{id}/export?fmt=fcstd`, `POST /models/{id}/slice`, `tools` in `GET /health`; see `docs/API.md`) and the web editor shows them only when configured. `slice_stl` runs PrusaSlicer with a throwaway `--datadir`, so only its built-in defaults apply (0.3 mm layers, 200 × 200 mm bed) and the user's profiles are never read or written.

## Out of scope

Native files of proprietary CAD systems are closed formats. The open-source OCCT reads none of them; readers exist only in vendor SDKs or commercial translators, which this project does not ship (D-005, D-009). The supported route for each is a STEP AP242 export from the source system.

| System | Files |
|---|---|
| CATIA V5/V6 | `.CATPart`, `.CATProduct` |
| Siemens NX | `.prt` |
| SolidWorks | `.sldprt`, `.sldasm` |
| Creo (Pro/ENGINEER) | `.prt`, `.asm` |
| Autodesk Inventor | `.ipt`, `.iam` |
| Solid Edge | `.par`, `.asm` |
| Parasolid | `.x_t`, `.x_b` |
| ACIS | `.sat`, `.sab` |
| JT | `.jt` |
