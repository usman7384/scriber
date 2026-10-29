# M5 parity: Onshape export (AP-8) and the Community tab (WP-10 web half)

Demo in `evals/src/partwright_evals/parity_m5_onshape.py` (`ROWS`, not yet in `parity.registry()`), offline test `evals/tests/test_parity_m5_onshape.py` (about 10 s), fixtures in `evals/parity/m5/onshape/`. Web: `apps/web/e2e/parity/community.spec.ts`, see `docs/agents/parity-web.md`.

## What was built

- Geometry: `export_onshape(api, design)` in `partwright_geometry.onshape_export` creates a document and one part studio per IR part through the existing `OnshapeApi` protocol (its `post` covers every create call, so the protocol is unchanged), then posts features in IR order: a variable per parameter, offset construction planes shared by sketches on the same plane, sketches named by IR sketch id, extrudes and holes named by IR feature name, holes placed by a points sketch at `hole_centres`. A non-OK feature status raises; anything it cannot map raises `UnsupportedExportError`. Scope and gaps are in `docs/INTEROP.md`.
- `RecordedOnshape` keeps the posted bodies (`posts`) and serves a list of recorded replies to repeated identical calls in order.
- Web: Community tab, Publish in the editor, fork provenance in the editor header and project cards, EN and DE strings.

## Measured (offline, scripted model)

| Row | Result |
|---|---|
| AP-8 | "Make the base plate 10 mm thick and open the motor bore to 24 mm" through `refine`: plate_thickness 6 to 10, bore_diameter 22 to 24, nothing else; 20 calls, all POST to `documents`, `partstudios`, `partstudios/features`; 0 translation, blob or import calls; 18 features (8 variables, 2 offset planes, 4 sketches, extrudes Base plate and Motor boss, holes Motor bore and Mounting holes), all OK; linked `Base plate.depth=#plate_thickness`, `Motor bore.holeDiameter=#bore_diameter`, `bore plane.offset=#plate_thickness + #boss_height`; 0 dangling feature references; refined part 61311.615 mm³ |
| WP-10 | web half pass, `parity-web-20261029-054713` (numbers in `parity-web.md`) |

AP-8 depends on the model only for the change request; a live `partwright-parity AP-8` run (after the module is registered) decides it. A live answer that adds or removes features no longer matches the 18 recorded replies and fails the row.

## Run

```
uv run pytest evals/tests/test_parity_m5_onshape.py services/geometry/tests/test_onshape_export.py services/geometry/tests/test_onshape.py
cd apps/web && npm run parity
```
