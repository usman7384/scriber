# M5 parity: API, app and context rows

Branch `feat/m5-platform`. Demos in `evals/src/partwright_evals/parity_m5_platform.py` (`ROWS`, not yet in `parity.registry()`), offline tests in `evals/tests/test_parity_m5_platform.py` (about 1 min), fixtures in `evals/parity/m5/platform/`. Each API demo drives the in-process app through `parity_api.serve` and writes `transcript.jsonl`.

## What was built

- API (`docs/API.md`): `POST /projects/{id}/designs` (build posted IR, no model), `POST /projects/{id}/sizing` (sizing XML through the D-031 adapter), `GET /materials`, `PUT /models/{id}/material`, `GET /models/{id}/sensitivities`, `POST /models/{id}/simulation`, `POST|GET /bugs`, `GET /bugs/{id}/screenshot`, `GET /usage`, `/community` (publish, list, get, unpublish, fork). Users are token names; `generation_limit` (default unset) gives 429 per user. Components carry the material's properties; models carry `forked_from`.
- IR: `partwright_ir.materials`, a table of eight materials (density, E, yield) with the datasheet or standard each value comes from. Geometry's `density()` now reads it (same values as before). It sits in the IR because geometry (mass) and the API (properties) both need it and may only share the IR.
- Context: `ingest_all` and `archive_files` ingest a folder and return a per-file outcome; one bad file is recorded, not raised. `partwright context add` takes folders and `--report`.
- CLI: `partwright pipe` posts sizing XML from stdin to a running API and saves the STEP.
- Geometry: describing a STEP with no faces now fails (a truncated file used to come back as an empty shape and count as parsed).
- Agent: the suggestion prompt's findings heading also names simulation.
- `examples/shadow_box.py`, `examples/phone_holder.py` and `docs/EXAMPLES.md`; an "Export to other CAD systems" section in `docs/INTEROP.md`.

## Rows (offline run, FakeLLM)

| Row | Demo measures | Offline |
|---|---|---|
| AP-6 | spanner STL → insert via the API; pocket wall points 0.9997–1.0000 mm from the tool outline (1074 samples, STL vertices and chord midpoints) | pass |
| AP-9 | `pipe` of `sizing.xml` → model with origin `sizing`, 0 LLM calls; IN-11 checks on the downloaded STEP: span 1000.0, chords 250.036/120.017, sweep 20.002°, dihedral 5.000°, twist 2.000°, 0.015 % chord | pass |
| DP-19 | phone width 75 → cradle inner width 75.500 at mid-lip height | pass |
| WP-10 | alice publishes, bob sees it, forks into his project with `forked_from`, edits thickness 5→8; the original stays at 5 | pass (API half; no web Community tab) |
| WP-11 | bug stored with model id, version, text, user and the PNG byte-identical | pass (API half; the web dialog posts this shape, no browser run against the live API) |
| WP-12 | limit 3: alice 202, 202, 202, 429; bob 202; unset limit: 11 of 11 generations | pass |
| CD-3 | mock FEA result 193.2 MPa vs 138 allowable (1.40×) on `mount_face` → proposal `thickness 4→5`, accepted, mock stress 123.65 MPa | pass offline (scripted proposal); the live model decides |
| CD-7 | sensitivities on the plate and the tab against closed forms (dV/dt, dm/dt, dV/dL, dV/dhole_d, dbbox/dparam): max relative error 8.7e-12 | pass |
| CX-12 | 50 STEP + 20 PDF from `legacy_archive.py`, one of each damaged on purpose: 68/70 parsed (97.1 %), both failures with an error in `ingest_report.json`, about 4 s | pass |
| CX-14 | "Aluminum 6061" → 2.70 g/cm³, 68.9 GPa (ASM MA6061T6) on the part; mass 127.753 g vs analytic 127.753 g | pass |
| EX-5 | AP242 STEP written and re-read by OCCT: volume drift 1.5e-16, bbox drift 0, 1 valid solid, material kept; docs section present | open: FreeCAD is not installed |
| EX-8 | not attempted | open |

## Mock FEA (CD-3)

`mock_fea` stands in for a solver: the tab is a cantilever fixed at `mount_face` with a tip load F, so the root bending stress is σ = 6 F L / (w t²). F is fixed by the fixture result (1.4 × 138 MPa at L 80, w 30, t 4 gives 193.2 N); the allowable is the 6061-T6 yield over a safety factor of 2. Any thickness above 4·√1.4 = 4.73 mm passes. The API part is real: `POST /models/{id}/simulation` turns each face group over its allowable into a finding and asks the agent's `suggest` for parameter changes, which are accepted through the suggestion route.

## Gaps

- EX-8 (SDF gyroid bracket → B-rep within 0.2 mm) not attempted: no marching-cubes or surface-nets code in the dependencies (scikit-image is absent), and a triangle-sewn B-rep of a gyroid is about 1e5 faces for OCCT to sew. Needs a meshing step and a decision on B-rep fitting first.
- EX-5's FreeCAD half was built later with FreeCAD 1.1.4 (`docs/agents/parity-freecad-tools.md`).
- Projects and models are not user-scoped; any token can read every project. The community listing is the shared space, not an access boundary.
- The shadow-box outline is the mid-height section, so it suits flat tools only.
- `partwright pipe` is tested against the in-process app, not a running server.
- `examples/` is type-checked with `mypy examples`; CI's mypy target list should add it.
- The parity rows are not registered in `parity.registry()` (integrator).
