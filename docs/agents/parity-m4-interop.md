# Parity M4: interop and downstream metadata

Branch `feat/m4-interop`. Closes offline, with the real geometry worker: **GE-12, GE-3, IN-10**. Advances **EX-4** (IR bundle half only; the FreeCAD `.FCStd` half is blocked). None of these rows uses the model, so the offline test and a live `scriber-parity` run measure the same thing.

## What landed

- **IR** (additive): `Part.face_groups`, each a snake_case name plus a face `Selector`. Compiled into a `FACES` table only when a design has groups, so existing designs compile byte-identically (`test_compile_golden.py`). The validator rejects duplicate names and selectors that point at unknown features.
- **Geometry, STEP**: parts with face groups or a material are written as AP242 through an XCAF document: group names become named faces, the material and its density become a material property. `LocalGeometry.step_metadata(path)` reads schema, body names, assembly paths, named face groups (count, area, centroid, normal) and materials from any STEP file. Other designs keep build123d's export.
- **Geometry, sketches**: `sketch_dof(design)` turns each sketch entity into lines, arcs, circles and points with candidate constraints in priority order (coincident, horizontal/vertical, tangent, radius, IR dimensions, plain positions). A candidate is kept only if it raises the rank of the constraint Jacobian, so the set has no redundant constraint; DOF = unknowns − rank. The solver then re-solves from a perturbed start and reports the largest deviation from the IR geometry. `remaining_dof` recounts from stored geometry and constraints.
- **Geometry, bundle**: `export_bundle` / `open_bundle` (zip: manifest, `design.json`, `model.py`, `params.json`, `features.json`, `sketches.json`, `model.step`). Opening checks the hash, that `model.py` replays from `design.json`, and recounts every sketch's DOF.
- **Geometry, Onshape**: `import_onshape(api, ref, step)` behind an `OnshapeApi` protocol, with `RecordedOnshape` replaying recorded responses. Sketches on default planes (lines, circles) and solid extrudes become IR with depth parameters cited to the feature; every other feature stays in the imported list unmapped.
- **Docs**: `docs/INTEROP.md` (supported paths, gaps, proprietary formats out of scope).
- **Evals**: `scriber_evals.parity_m4_interop.ROWS`; fixtures in `evals/parity/m4/interop/` (`make_fixtures.py` writes both STEP files; the Onshape responses are hand-written from the public API docs).

## Measured (offline run)

| Row | Result |
|---|---|
| GE-12 | AP242 STEP of the load bracket carries `mount_face` (area 4641.692, normal −Z, z = 0), `load_face` (314.159 = π·10², z = 21), `bolt_bores` (4 faces); material `6061 aluminium`, 2.70 g/cm³; same groups and material in the reopened bundle |
| GE-3 | 47 IR designs in the repo (worked examples, fixtures, live-run outputs), 60 sketches, 60 with 0 DOF, 0 unsupported, max re-solve deviation 7e-15; 755 constraints, 270 driven by IR expressions, 0 plain positions needed |
| IN-10 | AP242 gearbox: `gearbox/base_plate`, `gearbox/shaft_assembly/shaft`, `.../bearing`, `gearbox/cover`, all valid. Onshape mock: 10 features listed in order with ids and types, 8 mapped (4 sketches, 4 extrudes), mate connector and suppressed fillet kept unmapped; bodies Bracket and Pin; rebuilt IR matches the translated STEP per body (volume drift 5e-15); docs list CATIA, NX, SolidWorks, Creo, Inventor, Parasolid (and Solid Edge, ACIS, JT) as out of scope |
| EX-4 | bundle reopens with the feature tree and dependencies, constraints per sketch (28 and 3, DOF 0), rebuild volume drift 0; FCStd blocked: FreeCAD not installed; FeatureScript export not built. Demo reports **fail** |

## Run

```
uv run pytest evals/tests/test_parity_m4_interop.py services/geometry/tests/test_step_meta.py services/geometry/tests/test_sketcher.py services/geometry/tests/test_bundle.py services/geometry/tests/test_onshape.py services/ir/tests/test_face_groups.py
uv run python evals/parity/m4/interop/make_fixtures.py   # regenerates the STEP fixtures
```

## Gaps and gotchas

- EX-4's FCStd half was built later with FreeCAD 1.1.4 (`docs/agents/parity-freecad-tools.md`).
- GE-3: a coincidence that is only half redundant (a closed chain of collinear lines, as in the recorded "Stepped shaft" polygon with every point on y = 0) is kept as its independent axis (`distance_x`/`distance_y` = 0 between the two points); before, the whole coincidence was dropped and the polygon kept 1 DOF. Re-run 2026-10-29: 812 designs, 954 sketches, all 0 DOF, max re-solve deviation 6e-13.
- GE-3: no path or slot entity appears in the recorded designs; both are covered by unit tests (perimeters match build123d). A fillet next to an arc segment in a path is reported as unsupported, not counted. Airfoil sections are generated curves, not sketches. Constraints are not replayed in a FreeCAD Sketcher.
- Onshape: no HTTP client, no translation polling, sketch constraints not read, arcs/splines not mapped, `booleanScope` ignored. The mock was not captured from a live account.
- OCCT gotchas (commented in code): the STEP writer drops names of faces that carry their own location, so parts are flattened with `ShapeUpgrade_RemoveLocations` first; OCP's `FindAttribute` crashes when the attribute is missing, so `IsAttribute` is checked first; build123d's exporter always writes an AP214 header, so AP242 files go through our own XCAF writer.
- The IR JSON schema gained `face_groups`, so constrained decoding now allows it; prompts are unchanged.
