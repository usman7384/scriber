# Web parity demos (M3, `apps/web`)

Playwright specs under `apps/web/e2e/parity/`, one `test()` per checklist row, named with the row id first. They run against the mocked API (`e2e/mock-api.ts`), offline and deterministic. Each row writes screenshots, a video and `evidence.json` (`{row, passed, measured, note}`, the `Evidence` shape of `partwright_evals.parity`) to `evals/results/parity-web-<YYYYMMDD-HHMMSS>/<ROW>/`; `passed` is the Playwright verdict of that test.

## Run

```bash
cd apps/web
npm run parity      # playwright.parity.config.ts: own Vite server on 127.0.0.1:5199, video on, ~35 s
```

The run stamp is set once in the runner process (`PARITY_RUN`) and inherited by the workers. `npm run e2e` ignores `e2e/parity/`. The root `.gitignore` rule `evals/results/*/*/` hides the row folders, so committing evidence needs `git add -f`.

## Rows

Latest run: `evals/results/parity-web-20261029-021647/`, 13/13 pass.

| Row | Test | Measured | Status |
|---|---|---|---|
| WP-1 | `viewer.spec.ts` WP-1 | GLB bbox 120 x 80 x 6 mm; Top forward (0,0,-1) up (0,1,0); Front (0,1,0)/(0,0,1); Right (-1,0,0)/(0,0,1); orbit 42.9 deg at constant 300 mm radius | closed (web only) |
| VM-4 | `viewer.spec.ts` VM-4 | marker 0.19 mm from the see-through hole centre; hole Ø9.25 mm, 10.42 mm from the edge (top view, pixels); pop-up "needs ≥ 15 mm" and "keep hole centres x between -15 and 15" | web half; API leg mocked |
| WP-11 | `viewer.spec.ts` WP-11 | report `{model_id m1, version 1, text, screenshot}` with a 662 x 516 PNG of the viewer, 12 % part pixels | web half; apps/api has no `/bugs` route |
| PR-1 | `editor.spec.ts` PR-1 | one row per param (3 params, 2 scenarios), slider with API min/max, numeric field, unit | web half |
| PR-3 | `editor.spec.ts` PR-3 | off: slider drag to 174.3, 0 PATCH after 1 s, 1 PATCH after Enter; on: 1 PATCH 397 ms after release | closed (web only) |
| WP-3 | `editor.spec.ts` WP-3 | title from the API; chip Entire object, component (tree), Entire object, component (click in viewer), Entire object (click empty); Back and New generation reach the prompt | closed (web only); GE-10 titles are server side |
| WP-8 | `editor.spec.ts` WP-8 | model card and version thumbnails 256 x 256 PNG; after editing Hole X 20 to 15 a new URL with different pixels; gallery follows the latest | web half; regeneration on edit is apps/api |
| WP-2 | `project.spec.ts` WP-2 | 3 files uploaded (image, mesh, spec), 1 generate request carrying their 3 ids | closed (web only) |
| WP-4 | `project.spec.ts` WP-4 | 4 chips, each fills the prompt box | closed |
| WP-5 | `project.spec.ts` WP-5 | Projects, Library, Settings (theme works), Help, project Models list, Context manager, API docs popup | closed (web only); `/docs` stubbed |
| WP-9 | `project.spec.ts` WP-9 | Library lists 3 parts from 2 projects, newest first, thumbnails loaded | closed (web only) |
| CX-2 | `context.spec.ts` CX-2 | 7 columns, 6 files, search "motor" gives 2, select shows facts, delete leaves 5 rows and 7 of 8 graph nodes | web half; graph removal is services/context (`test_delete_document_removes_its_records`) |
| CX-5 | `context.spec.ts` CX-5 | 8 nodes and 4 edges == API counts, counter text, fullscreen 1280 x 900, exits with Escape and button | closed (web only) |

## How the mock stays honest

- **Real geometry.** `e2e/fixtures/edge-plate-x20.*` and `edge-plate-x15.*` are geometry-service output (build123d, DFM, pyrender thumbnail) for the `test_dfm.plate(x)` design: 60 x 40 x 5 mm, Ø10 hole at x = 20 (fails 1.5 x D) and x = 15 (passes). `plate.png` is the thumbnail of the existing `plate.glb`. A `Scenario` in `e2e/fixtures.ts` maps parameter values to these prebuilt outputs; a value without one gets a 404.
- **Camera read-out.** `e2e/parity/viewer.ts` imports the react-three-fiber module the dev server already loaded (same URL, same instance) and reads `_roots` for the live camera. Dev-server only.
- **Hole location.** VM-4 flood-fills the transparent canvas pixels under the marker in top view; an enclosed region is the through-hole.

## Product changes

- Main nav: Projects, Library, Settings, Help, API. New pages `LibraryPage` (all models of all projects, newest first), `SettingsPage` (theme, API server), `HelpPage`. The theme toggle moved from the top bar to Settings (`src/theme.ts`, passed through the outlet context). A production server must also serve `index.html` for `/library`, `/settings`, `/help`.
- Editor header: "New generation" link to the project prompt.
- Mock API: per-version GLB and PNG thumbnail at `/models/{id}/versions/{n}/thumbnail` (as in apps/api), upload and ingest jobs, `POST /bugs`, a second project, a graph derived from the current files.

## Gaps

- Rows marked "web half" need the live API leg to close: findings and thumbnails through apps/api, a `/bugs` route, KG deletion end to end.
- Library is client-side fan-out (one request per project); a `GET /models` would replace it.
- One transient `main-flow.spec.ts` timeout on the first run after edits (cold Vite); five reruns passed.
