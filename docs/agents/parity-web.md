# Web parity demos (M3 and M5, `apps/web`)

Playwright specs under `apps/web/e2e/parity/`, one `test()` per checklist row, named with the row id first. They run against the mocked API (`e2e/mock-api.ts`), offline and deterministic. Each row writes screenshots, a video and `evidence.json` (`{row, passed, measured, note}`, the `Evidence` shape of `partwright_evals.parity`) to `evals/results/parity-web-<YYYYMMDD-HHMMSS>/<ROW>/`; `passed` is the Playwright verdict of that test.

## Run

```bash
cd apps/web
npm run parity      # playwright.parity.config.ts: own Vite server on 127.0.0.1:5199, video on, ~50 s
```

The run stamp is set once in the runner process (`PARITY_RUN`) and inherited by the workers. `npm run e2e` ignores `e2e/parity/`. The root `.gitignore` rule `evals/results/*/*/` hides the row folders, so committing evidence needs `git add -f`.

## Rows

Latest run: `evals/results/parity-web-20261029-191556/`, 27/27 pass (adds EX-4 and VM-9 web halves; earlier `parity-web-20261029-054713` 25/25, M3 run `parity-web-20261029-021647`).

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
| AS-1 | `model.spec.ts` AS-1 | components API lists `plate` and `cube` (parent plate, joint cube_on_plate); clicking each part in the Front view selects tree ids `plate`, `cube`; refine sends `target: cube` | web half; the list route is real in apps/api (`test_assembly.py`), mocked here |
| PR-6 | `model.spec.ts` PR-6 | top face picked at z 5.000, normal (0, 0, 1); driver Thickness; offset +2 sends `{values: {thickness: 7}}`; only `thickness` changed (5 to 7); GLB height 7.0000 mm | web half; the API half is `apps/api/tests/test_faces.py` (real route and kernel: driver thickness rate 1, bbox z +2 ±0.01, other params equal); no live demo |
| PR-7 | `editor.spec.ts` PR-7 | 2 suggestions shown; Ignore leaves 1 version and 0 PATCH; Accept gives v2 origin `suggestion`, Hole X 20 to 15, findings 1 to 0; statuses accepted, ignored | web half; suggestions in a panel, not anchored in 3D |
| PR-10 | `model.spec.ts` PR-10 | labels `L 120.0 mm`, `W 80.0 mm`, `H 5.0 mm` and `L 60.0 / W 40.0 / H 24.0 mm`, inside the view; GLB box equals metrics.bbox to 0.01 mm | web half; API half is `parity-20261029-025007` |
| EX-6 | `share.spec.ts` EX-6 | link `/shared/s1`; the visitor page makes only `GET /s/s1` and `GET /s/s1/files/glb`; 0 editable fields and 0 edit buttons; after Revoke the page shows "share link not found or revoked" | web half; API half is `parity-20261029-025007` |
| WP-6 | `project.spec.ts` WP-6 | SSE progress events 10, 40, 60, 70, 100; bar values seen 10, 40, 60, 70, 100 (150 ms apart) | web half; the values are apps/api `work.PROGRESS`, the stream is mocked |
| WP-10 | `community.spec.ts` WP-10 | Publish in the editor sends `{model_id: m1, version: 1}`; the Community page lists 2 parts newest first (`v1 · by local`, `v2 · by alice`), thumbnails 256 px; Fork into Bracket lab posts `/community/c5e1a9b3d7f2/fork {project_id: p1}`; the copy opens in the editor (60 x 40 x 5 mm, Hole X 15, origin fork) and its card in the project shows "Forked from Edge test plate v2 by alice" | web half; API half is `parity-20261029-052939` |
| WP-13 | `language.spec.ts` WP-13 | 199 language-dependent strings; 144 shown on ten pages in EN (Community page added), all 144 German counterparts shown in DE, 0 English left; was 191 / 140 on nine pages in EN, all 140 German counterparts shown in DE, 0 English left (text nodes, aria-label, placeholder, title, alt, hidden dialogs and tooltips included); select, `html lang` and localStorage stay `de` after reload | closed (web only) |
| CX-1 | `context.spec.ts` CX-1 | 6 files (PDF, STEP, MD, TXT, CSV, PNG) in one upload; each progress bar 0 then 100; list returns 6 processed | web half; API half is `parity-20261029-025007` |
| CX-3 | `context.spec.ts` CX-3 | chosen `nema17-motor.step`, `plate-design-rules.md`; generate sends `context_ids` f2, f3 exactly; both show Used in "Sensor plate", others unchanged; the link opens the model | web half; recording the ids on the generation is apps/api |
| CX-6 | `context.spec.ts` CX-6 | before: 6 files, 21 facts, 2 rules, 1 used, score 132/400, level 1; after 2 uploads and 1 generation: 8, 23, 2, 2, score 176/400, level 1; delta 44 = 10·2 + 2·2 + 20·1; UI equals the formula both times | web half; API half is `parity-20261029-025007` |
| WP-14 | `project.spec.ts` WP-14 | 3 UI steps (type the prompt, Generate, Download STL); `motor-holder-v1.stl`, 2036 triangles, 60 x 40 x 24 mm, 15481 mm³, watertight and consistently oriented | web half; generation is mocked and VM-9 (slicer) is not run |
| EX-4 | `tools.spec.ts` EX-4 | Export, FreeCAD (.FCStd) on the base plate saves `base-plate-v1.FCStd`, 15265 bytes, identical to FreeCAD 1.1.4's output, a zip with `Document.xml`; on the stack assembly the editor shows "this design has no FreeCAD export: assembly joints and placements have no FreeCAD export yet"; with `tools.freecad` false the item is absent | web half; the route is real in `apps/api/tests/test_tools.py` (FreeCAD faked, plus a real run when `PARTWRIGHT_FREECAD` is set) |
| VM-9 | `tools.spec.ts` VM-9 | Check printability on the motor holder: 1 `POST /models/m1/slice`, shows PASS "80 layers, 1.98 MB of G-code", watertight, 0 warnings, 0 errors, placed after the findings; with `tools.prusaslicer` false the button is absent | web half; report is PrusaSlicer 2.9.6 output, the route is real in `apps/api/tests/test_tools.py` |

## How the mock stays honest

- **Real geometry.** `e2e/fixtures/edge-plate-x20.*` and `edge-plate-x15.*` are geometry-service output (build123d, DFM, pyrender thumbnail) for the `test_dfm.plate(x)` design: 60 x 40 x 5 mm, Ø10 hole at x = 20 (fails 1.5 x D) and x = 15 (passes). `plate.png` is the thumbnail of the existing `plate.glb`. A `Scenario` in `e2e/fixtures.ts` maps parameter values to these prebuilt outputs; a value without one gets a 404.
- **Camera read-out.** `e2e/parity/viewer.ts` imports the react-three-fiber module the dev server already loaded (same URL, same instance) and reads `_roots` for the live camera. Dev-server only.
- **Hole location.** VM-4 flood-fills the transparent canvas pixels under the marker in top view; an enclosed region is the through-hole.
- **More real geometry.** `e2e/fixtures/make_fixtures.py` (`uv run python apps/web/e2e/fixtures/make_fixtures.py`) rebuilds `base-plate-t5/t7`, `stack` and `motor-holder` with `LocalGeometry`: GLB, thumbnail, STL for the motor holder, and a JSON with the version's params, metrics and findings. The base plate is the `apps/api` test plate; the stack is the D-033 cube-on-plate assembly; the motor holder is a hand-written IR standing in for the model's answer to the WP-14 prompt.
- **Mocked routes follow apps/api.** Components, face-driver, suggestions (ignore returns the suggestion, as the route does; `docs/API.md` says 204), shares with `/s/{id}` and `/s/{id}/files/{kind}` and revoke, export with the API's attachment file name, ingest and generate steps with `progress` from `work.PROGRESS`, KB stats counted like `store.counts` and scored with the `LocalContext.stats` formula.
- **Streaming.** With `api.drip` set, each SSE response carries the next event and `retry: drip`, so the browser reconnects and the bar is sampled while events arrive. Chromium's request interception does not show `Last-Event-ID`, so the mock keeps the position per job.
- **Scene probe.** `viewer.ts` `probe` reads part boxes by glTF node name and projects CAD points to the page through the live camera; AS-1 clicks the projected part centres and PR-6 the plate top.
- **External tools.** `GET /health` reports `tools` (both on by default in the mock, off per test). The FCStd export and the slice route answer with the API's status codes and wording (503 unconfigured, 422 `this design has no FreeCAD export: ...`); the bytes and the report are real FreeCAD and PrusaSlicer output written by `make_fixtures.py` (`base-plate-t5.FCStd`, `external-tools.json`; needs both variables).
- **Downloads.** A browser download bypasses Playwright's interception, so WP-14 fetches the downloaded URL through the mock after clicking the link (the Vite proxy logs one refused connection for the browser's own attempt).

## Product changes

- Main nav: Projects, Library, Settings, Help, API. New pages `LibraryPage` (all models of all projects, newest first), `SettingsPage` (theme, API server), `HelpPage`. The theme toggle moved from the top bar to Settings (`src/theme.ts`, passed through the outlet context). A production server must also serve `index.html` for `/library`, `/settings`, `/help`.
- Editor header: "New generation" link to the project prompt.
- Mock API: per-version GLB and PNG thumbnail at `/models/{id}/versions/{n}/thumbnail` (as in apps/api), upload and ingest jobs, `POST /bugs`, a second project, a graph derived from the current files.

## Product changes (M5)

- Editor: component tree from `GET /models/{id}/components` (nested by parent, selection by API part id, refine `target` is the id); Select face in the viewer toolbar maps a pick to its driving parameter through `POST /models/{id}/face-driver` and offsets it; a Suggestions panel with Suggest, Accept and Ignore.
- Share: the link is the web page `/shared/{id}` (read-only viewer, title, parameters); Revoke deletes the share. A production server must serve `index.html` for `/shared/*`.
- Progress: timeline progress bar from `Step.progress`; one progress bar per uploaded file.
- Context: a checkbox per file and "Use selected as context" open the prompt with those files as `context_ids`; Used in links the models by title.
- Project page: a finished generation offers Download STL next to Open model.
- Language: EN/DE selector in the top bar (`src/i18n.ts`), remembered in localStorage.
- Community: a Community tab (`/explore`, since `/community` is the API path the dev proxy forwards) lists every publication with thumbnail, title, version, author and date, and forks one into the project picked in "Fork into project"; the editor has Publish and shows "Forked from ... by ..." for a fork, as does its card in the project. A production server must serve `index.html` for `/explore`.
- API: `POST /models/{id}/face-driver` (`apps/api/.../routes/faces.py`, lookup `partwright_ir.face_driver`, tests `test_faces.py` and `services/ir/tests/test_drivers.py`).

## Gaps

- Rows marked "web half" need the live API leg to close: findings and thumbnails through apps/api, a `/bugs` route, KG deletion end to end; for M5, a live generation of the WP-14 prompt with VM-9 slicing, a live PR-6 and AS-1 run through apps/api, and SSE progress from a real job.
- Face edit covers extrude cap faces on XY/XZ/YZ or unrotated datum planes; side walls, holes and parts placed by a joint have no driver yet. The picked face is not highlighted.
- Suggestions are a panel, not bubbles in the 3D view.
- The viewer maps glTF node names to API ids by part name; two parts with the same name would be ambiguous until the exporter names nodes by IR id.
- Dates follow the browser locale, not the selected language; API text (titles, findings, step messages, file names, example prompts) is not translated.
- Community: no Unpublish button yet (the API has `DELETE /community/{id}`); the page does not mark which publications are the viewer's own.
- Library is client-side fan-out (one request per project); a `GET /models` would replace it.
- One transient `main-flow.spec.ts` timeout on the first run after edits (cold Vite); five reruns passed.
