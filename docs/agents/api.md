# M3 API (build agent)

Branch `feat/api-m3`. New `apps/api` (distribution `partwright-api`, import `partwright_api`): a FastAPI app implementing `docs/API.md`, plus a thumbnail renderer in `services/geometry` and `partwright serve` in the CLI.

## What was built

- `create_app(settings, llm, geometry, context, transport=None)` builds the app; every dependency is injected. `transport` is the httpx transport for outbound calls (webhooks, Ollama ping) so tests can stub them.
- Storage under `data_dir`: `api.sqlite` (SQLAlchemy Core tables in `db.py`: projects, files, models, versions, jobs, job_steps, tokens, shares, hooks), version folders `models/<model_id>/v<n>/` in the CLI layout (`attempt_k/`, `steps.json`, `params.json`, `result.json`, `model.step|stl|glb|py`, `design.json`, `OK`) plus `thumbnail.png`, uploads in `uploads/<project>/<file_id>/<name>`, and the project context in `context/` (the same folder the CLI uses).
- Jobs (`jobs.py`): in-process asyncio dispatcher over the SQLite job table (D-008). Generate, refine and edit share one `asyncio.Semaphore(1)` (the GPU lane); ingest and params run beside it. The blocking agent, geometry and context calls run in worker threads (`asyncio.to_thread`). Each step is written to `job_steps` and pushed to SSE subscribers with its sequence number, so `GET /jobs/{id}/events` replays persisted steps, then live ones, and honours `Last-Event-ID`. On startup, `queued` and `running` jobs become `failed` with error `interrupted`.
- The single warm CAD worker speaks a one-request-at-a-time pipe protocol, so `SerialGeometry` puts a lock around it; the context service gets one lock too. The context's `describe` must be the serialized geometry's (`serve` and the tests do this).
- `PATCH /models/{id}/params` and `/api/v1/edit` apply the values to the latest successful design and rebuild without any LLM call. Edit also checks that every parameter is used by that component alone.
- Circular design: when an uploaded file replaces a file of the same name, the facts whose name, value, unit, tolerance or count changed are passed to `LocalContext.stale` before the old document is deleted; deleting a file does the same with all its facts. Affected models are marked stale (listed as `stale` in `GET /projects/{id}/context` and on each Model), and `version.stale` goes to hooks. A new successful version clears the flag. Successful versions are recorded in the knowledge graph as `<model_id>/v<n>`.
- Webhooks: `version.created` `{model_id, version, files}` (absolute URLs from `settings.public_url`), `job.failed` `{job}`, `version.stale` `{project_id, file_id, model_id, versions, changed_facts}`. Delivery retries 5xx and connection errors with exponential backoff (`hook_attempts`, default 4).
- Tokens: stored as SHA-256 digests; `Authorization: Bearer` or `X-API-Token`. When `auth: tokens` and no token exists yet, `POST /tokens` is open so the first token can be created.
- Observability: structlog JSON lines on stderr; an ASGI middleware binds `request_id` (from `X-Request-ID` or generated, echoed in the response) and logs each request; job tasks inherit it and bind `job_id`, including in worker threads. OpenTelemetry is not wired.
- Thumbnails (WP-8): `partwright_geometry.thumbnail.render_thumbnail` (trimesh + pyrender offscreen, 256 px, isometric, Y-up glTF) runs as the worker op `thumbnail`; `LocalGeometry.thumbnail()` calls it. pyrender is imported inside the function, so a machine without OpenGL still builds parts. Any failure logs `thumbnail_unavailable` and the version has no thumbnail; the job never fails for it. Measured here: 5 s for the first render in a worker (GL init), about 0.15 s after.

## Run it

```bash
uv run partwright serve          # host, port and auth from the api: section of config.yaml
# http://127.0.0.1:8000/docs for the OpenAPI UI, /openapi.json for the schema
```

Smoke run on 2026-10-26 with `qwen3.5:4b`: "Mounting plate 80 x 60 x 5 mm with four M6 clearance holes" streamed requirements, emit, check (hole-to-edge rule), repair, done over SSE in 98 s; 4/4 checks, 256 px thumbnail. Three `PATCH /params` edits then took 296 to 328 ms to rebuild and 0.9 to 1.1 s per job including thumbnail, shape descriptor and graph recording.

## Deviations from `docs/API.md`

All additive except the status codes:

1. Status codes: creates return 201 (projects, shares, hooks, tokens, restore), job submissions 202.
2. `GET /projects/{id}/context` also returns `stale: [model_id]`; `Model` has `stale: bool`.
3. `Version` has `attachments: [file_id]` (IN-16/IN-17 provenance) and `changes` (the IR diff against the version it was made from: params old/new, features added/removed/changed; CD-2). `POST /models/{id}/refine` and `/api/v1/modify` accept `attachments`.
4. `GET /models/{id}` returns the Model fields plus `version` (the latest Version); `GET /s/{id}` has the same shape.
5. New file routes the contract needs but does not list: `GET /models/{id}/versions/{n}/thumbnail` (PNG) and `GET /s/{share_id}/files/{step|stl|glb|py|ir|thumbnail}` (no auth, so a shared viewer can load the GLB).
6. `POST /batch` returns one `generate` job per prompt; the `batch` job kind is unused.
7. Hook events also include `version.stale`.
8. `/api/v1/generate` takes `image` and `mesh` as file ids already uploaded to the `default` project (created on first use); `/api/v1/download` returns the latest version.
9. `/health` reports `ollama: false` when no Ollama host is configured (tests). Generate, refine, batch, modify and uploads return 503 when a configured Ollama does not answer `/api/version`.

## Decisions

- Own version store instead of sharing `partwright_cli.store`: the CLI now imports the API (`serve`), so the API cannot import the CLI, and `services/agent` is off limits. `disk.py` repeats the CLI's 20-line save routine and keeps the same layout. Moving `store` into a shared module (agent or a small `partwright_store`) is the clean fix; it is the integrator's call.
- Layering: `partwright_evals > partwright_cli > partwright_api > partwright_agent > geometry | context > ir`. Only the CLI imports the API.
- Version numbers come from the folders on disk (as in the CLI), so a crashed job leaves a gap instead of reusing a number.
- The job table and steps are portable SQLAlchemy Core; the only SQLite-specific code is the URL and WAL pragma in `db.py`.

## Changes outside `apps/api`

- `services/geometry`: new `thumbnail.py`, worker op `thumbnail`, a three-line `LocalGeometry.thumbnail()` method (the brief named only the module and the op, but the API cannot reach the op without it), `tests/test_thumbnail.py`, and deps `pyrender==0.1.45`, `pyglet==2.1.19`, `pillow==13.0.0`.
- `apps/cli`: `partwright serve`, an `api:` section in `Config` and `config.yaml`, deps `partwright-api` and `uvicorn==0.54.0`.
- Root `pyproject.toml`: workspace member, sources, mypy path, isort, import-linter root package, layers, kernel contract.

## Rows advanced (evidence in `apps/api/tests`)

| Row | Test | Status |
|---|---|---|
| AP-1 | `test_access.py::test_tokens_guard_every_route_when_enabled` | Bearer and X-API-Token accepted, revoked token 401 |
| AP-2 | `test_v1.py::test_generate_alias_uses_the_default_project` | plumbing with FakeLLM (job id, ≥1 hole); angled feature needs the live model |
| AP-3 | `test_v1.py::test_modify_alias_changes_the_thickness`, `test_models.py::test_refine_makes_the_plate_thicker` | +10 mm ±0.01 (scripted answer) |
| AP-4 | `test_v1.py::test_edit_alias_changes_only_that_component` | other part's metrics unchanged; foreign params 400 |
| AP-5 | `test_v1.py::test_download_alias_returns_each_format`, `test_models.py::test_export_formats_are_valid_files` | STEP reloads with same volume ±1e-6, STL watertight, GLB magic; Khronos validator not run |
| AP-7 | `test_models.py::test_batch_runs_every_prompt` | 10 prompts, 10 done, listable |
| GE-9 | `test_models.py::test_batch_variants_have_their_own_hole_counts` | 3 variants, 4/6/8 holes (scripted); rib variants and the 100-sweep not run |
| PR-2 | `test_models.py::test_params_patch_rebuilds_without_the_llm` | no LLM call, centres 90 ±0.01 apart, median rebuild < 1 s |
| PR-9 | `test_models.py::test_history_with_thumbnails_and_restore` | 4 versions with prompt and PNG, restore v1 params equal |
| EX-6 | `test_access.py::test_share_links_are_read_only_and_revocable` | unauthenticated view and GLB, writes 401, revoke 404 (UI viewer is web's) |
| EX-7 | `test_access.py::test_webhook_retries_on_server_errors` | `{model_id, version, files}` posted, two 503s retried |
| CD-1 | `test_context.py::test_spec_change_marks_the_model_stale_and_notifies_hooks`, `test_deleting_a_used_file_marks_its_models_stale` | stale detection, hook, old version kept; regeneration is not auto-triggered |
| CD-2 | `test_models.py::test_params_patch_rebuilds_without_the_llm`, `test_history_with_thumbnails_and_restore` | `changes` lists old/new params; triggering source is `origin` + `prompt`; no prose report |
| WP-6 | `test_jobs.py::test_generate_streams_steps_then_done` | ordered SSE steps then `done`, Last-Event-ID resume (no percentage) |
| WP-7 | `test_jobs.py::test_running_jobs_become_interrupted_on_restart`, `test_access.py::test_failed_jobs_notify_hooks_and_log_with_ids` | queued/running/done/failed; failure log line has job_id and request_id |
| WP-8 | `test_models.py::test_generated_model_lists_versions_with_metrics_files_and_thumbnail`, `test_missing_thumbnail_does_not_fail_the_job`, `services/geometry/tests/test_thumbnail.py` | 256 px PNG per version, regenerated on every edit; fallback tested |
| IN-16 | `test_context.py::test_attachments_ground_the_design_and_are_recorded` | prompt + image + spec recorded; spec facts reach the prompt and become a check, and vanish when the spec is left out (scripted model, so params cannot differ) |
| IN-17 | same test | refine with an image attachment records its id |

## Known gaps

- CD-1 needs auto-regeneration of stale models; only detection and notification exist.
- Images are recorded as attachments but not sent to a vision model (M4).
- A replaced file gets a new document id, so models derived from its unchanged facts lose their graph links (they are not marked stale, which is right, but later changes to those facts will not find them).
- Rule edits (`PUT /rules`) do not mark models stale; rules link to parts by `constrains`, which `stale()` does not follow.
- Shutdown does not wait for running jobs; they come back as `interrupted`.
- Thumbnails on headless Linux need `PYOPENGL_PLATFORM=egl` or `osmesa`; not tried. `test_thumbnail_is_a_256_px_png` and the WP-8 API test need OpenGL.
- Step thumbnails (optional) are not rendered.
- Starlette warns that its TestClient will move to `httpx2`; harmless for now.
