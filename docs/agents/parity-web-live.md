# Web parity rows run live (`apps/web/e2e/live`)

The web half of twelve rows, run end to end: the Vite dev server against `scriber serve` with the configured default model (`scriber-ir:4b-s2` through Ollama), a fresh context store, the real geometry worker and real thumbnails. No route is mocked. Evidence has the shape of the mocked suite (`docs/agents/parity-web.md`): screenshots, a video and `evidence.json` per row under `evals/results/parity-web-live-<stamp>/<ROW>/`.

## Run

```bash
cd apps/web
export SCRIBER_PRUSASLICER=.../PrusaSlicer-2.9.6/prusa-slicer-console.exe   # WP-14 slices the downloaded STL
npx playwright test -c playwright.live.config.ts                             # ~8 min on a 6 GB GPU
```

`playwright.live.config.ts` copies `config.yaml` into a new `%TEMP%/scriber-live-*` folder with `data_dir`, `output_dir` and `api.port` (8765) pointed there, starts the API and a Vite server on 5198 (`SCRIBER_API_URL` sets the dev proxy target), and stops both after the run. The user's `data/` is never touched; the next run deletes earlier temp folders (the API holds its SQLite files until Playwright stops it, after global teardown). One worker, since generations share the GPU. Kernel-side checks (trimesh, PrusaSlicer, IN-11 section fits) run through `e2e/live/checks.py` in the repo's Python environment. `npm run e2e` ignores `e2e/live/`.

Setup goes through the deterministic routes where the row is not about generation: IR posted to `POST /projects/{id}/designs` (`e2e/live/designs.ts`), multipart uploads, sizing XML through `scriber pipe`. The model is used in CX-6 (one grounded generation) and WP-14 (prompt to STL).

## Rows

Run `evals/results/parity-web-live-20261029-200716/`: 12/12 pass.

| Row | Measured live |
|---|---|
| CX-1 | 6 files (pdf, step, md, txt, csv, image) in one UI upload; each progress bar 0 then 100; API lists 6 processed |
| CX-2 | 7 columns, 6 rows; "motor" gives 2; holes.csv shows 10 facts; deleting notes.txt leaves 5 rows in the UI and the API, its 3 graph nodes (document, fact, chunk) are gone from the API graph and the UI graph (41 to 38 nodes) |
| CX-6 | UI card equals API stats equals the formula at three stages: empty 0/100; 2 uploads 30/100; 1 grounded generation (done) 50/100, used +1, delta 20 |
| EX-6 | link `/shared/{id}`; the visitor page makes only `GET /s/{id}` and `GET /s/{id}/files/glb`; 0 editable fields, 0 edit buttons; write on the share 405; after Revoke the page shows "share link not found or revoked" and the API 404 |
| WP-11 | one stored bug `{model_id, version 1, text, user local}`; the 662 x 516 PNG read back from `/bugs/{id}/screenshot` is byte-identical to the one the dialog sent |
| WP-14 | 3 UI steps; generation done in 99 s, 5/5 requirement checks; STL 60 x 40 x 4 mm, 1028 triangles, watertight, consistent winding; PrusaSlicer exit 0, manifold, 13 layers, no warnings or errors |
| AP-9 | `scriber pipe` with no UI input: model v1 origin `sizing`; IN-11 9/9 on the saved STEP (span 1000, chords 250.04/120.02, sweep 20.00, dihedral 5, twist 2, airfoil 0.015 % chord); the editor shows it at 301.9 x 1000.0 x 65.3 mm |
| PR-6 | top face picked at z 5, normal (0, 0, 1); `PATCH {values: {thickness: 7}}`; v2 origin params, only thickness changed (5 to 7), API bbox 120 x 80 x 7, GLB height 7 |
| PR-10 | base plate labels L 120.0 / W 80.0 / H 5.0 mm, stack 40.0 / 40.0 / 50.0 mm, inside the view; GLB box equals `metrics.bbox` |
| VM-4 | API finding `min_hole_edge_ratio` (required 15 mm) and its suggestion shown in the pop-up; marker 0.19 mm from the hole centre; hole Ø9.25 mm, 10.42 mm from the edge (pixels) |
| AS-1 | components API `plate`, `cube` (parent plate, joint cube_on_plate); clicking each part in the Front view selects the same id; cube nested under plate |
| WP-8 | card and version thumbnails 256 x 256 PNG from apps/api; editing Hole X 15 to 10 gives v2 with a new thumbnail URL and 1.2 % changed pixels; the gallery follows the latest |

## Product fix

- `POST /projects/{id}/context` read only the multipart field `files`, while `docs/API.md` and the web client send `files[]`, so every upload from the UI was a 422. The route now takes both (`test_upload_takes_the_contract_field_name`).

## Gaps

- WP-14 uses "mounting plate 60 x 40 x 4 mm with two M3 holes 48 mm apart". The checklist's prompt ("motor holder for 28 mm motor, 2 M3 screws") fails its requirement checks after 6 attempts with the default model (probe 2026-10-29: 129 s, bounding box never 28 mm, no M3 holes), so WP-14 is not closed by this run.
- CX-6's generation names the sizes in the prompt; "mounting plate to the selected spec" with the same file selected fails after 6 attempts (twice), so grounding from the file alone is a model gap.
- Generations are not reproducible across runs on this machine even with seed 0: the WP-14 prompt passed three times by curl and once through the UI, and failed once through the UI with a different first answer. Ollama is shared with other processes, which may batch requests.
- AS-1 does not run a refine with the selection as target (a model call); the mocked suite checks the request.
- VM-4's plate has an error-severity finding, so its only version is `failed`; the editor still shows it with the finding.
