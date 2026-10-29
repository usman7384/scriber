# Interoperability

What goes in and out of Partwright, and what does not. Everything here runs offline on open code (OCCT through build123d).

## Supported

| Path | Direction | What survives | Test |
|---|---|---|---|
| STEP AP242 (`.step`, `.stp`) | in | body names and assembly paths, named faces, materials and densities, solids | `test_parity_m4_interop` IN-10, `test_step_meta.py` |
| STEP AP242 | out | body names, named face groups (`mount_face`, `load_face`, ...), material and density per part. Written only when the design has face groups or materials; otherwise build123d's AP214 export is used unchanged | GE-12 |
| STL, OBJ | in | mesh descriptor only (bbox, area, watertight volume) | `test_import.py` |
| STL, glTF (`.glb`) | out | tessellation for viewing and printing | EX-2, EX-3 |
| IR bundle (`.zip`) | out and in | `design.json` (the IR), `model.py`, `params.json`, `features.json` (ordered tree with dependencies), `sketches.json` (geometry, constraints and DOF per sketch), `model.step`. Reopening checks the hash, that `model.py` replays from `design.json`, and recounts every sketch's DOF | EX-4 (bundle half), GE-3 |
| Onshape part studio | in | feature list (id, name, type, suppression), part names and materials, a STEP translation; sketches on the default planes (lines, circles) and solid extrudes (new, add, remove; blind or through all) become IR | IN-10, against a recorded mock |
| Onshape part studio | out | native features, no STEP: every parameter as a variable (`assignVariable`), sketches on Top/Front/Right or offset construction planes (lines, circles), extrudes (new, add, remove, intersect; blind, symmetric, through all, up to next) and holes (simple, counterbore, countersink at the IR hole centres). Features carry the IR names (sketch ids, feature names, parameter names); depths, diameters and offsets that are a parameter or a sum of parameters stay linked as `#name` expressions | AP-8, against a recorded mock |

## Export to other CAD systems

CATIA, NX, SolidWorks and Creo all import STEP, so STEP is the export path to them: AP242 (product structure, part names, named face groups, materials) when the design has face groups or materials, AP214 otherwise. Download it from `GET /models/{id}/export?fmt=step` or the IR bundle.

- Tested: an OCCT round trip (EX-5): write the STEP, read it back, compare volume and bounding box (drift below 1e-6), solid count, validity, schema and material.
- Not tested: opening the STEP in another CAD system. FreeCAD (open source, OCCT-based) is the planned check and is not installed on the build machine; none of the proprietary systems are available.
- Gaps: no PMI (GD&T, dimensions, tolerances), no feature history (other systems get a dumb solid), no native formats, no assembly constraints (mates travel only in our IR bundle), and colours are not written.

## Not yet built

- **FreeCAD `.FCStd`** (D-007): needs FreeCAD 1.1 installed (about 1 GB, LGPL, run as a subprocess with `FreeCADCmd`). Not installed on the build machine, so the emitter has not been written; an untested emitter would be a stub.
- **FeatureScript export**: not built.
- **Onshape export gaps** (`export_onshape` in `partwright_geometry.onshape_export`): only the `OnshapeApi` protocol and a recorded replay, no HTTP client; the recorded session (`evals/parity/m5/onshape/`) was written from the public docs as we read them, not captured from a live account, so feature and parameter ids are unverified against a real server. Sketch geometry is sent as numbers with no sketch constraints. Fillets, chamfers, shells, patterns, revolves, lofts, rounded rectangles, slots, paths, subtracted profiles, two-sided extrudes, tapers and sketches on faces or datums raise `UnsupportedExportError` instead of being dropped. Holes drill against the sketch normal (Onshape's convention), so a hole plane must be the entry face; tapped holes go out as their tap drill; blind holes keep Onshape's default tip. Each IR part gets its own part studio, next to the document's default empty one.
- **Onshape import gaps**: sketch constraints and dimensions are not read (we derive our own, see GE-3), arcs and splines are not mapped, `booleanScope` is ignored (add and remove act on the latest new body), the STEP translation is not polled, and no HTTP client exists: only the `OnshapeApi` protocol and the recorded replay. The recorded responses follow the public API docs ([features](https://onshape-public.github.io/docs/api-adv/featureaccess/), [translations](https://onshape-public.github.io/docs/api-adv/translation/)) as we read them; they were not captured from a live account.
- **PMI** (GD&T, dimensions) in STEP AP242: not written or read.

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
