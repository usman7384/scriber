# M3 parity: API and agent rows

Demos for the M3 rows owned by api, agent, context (CX-1/3/6), geometry (PR-10) and eval (PF-4), in `evals/src/scriber_evals/parity_m3.py` (`ROWS`). Each demo drives the real FastAPI app in-process (`parity_api.serve`: `create_app` with a `TestClient`, the rig's geometry, a `LocalContext` with the hash embedder) and writes `transcript.jsonl` (every request and response), `api.log` (the structlog JSON lines) and row artifacts (`sse.jsonl`, `plm.jsonl`, `change_report.md`, `validator.json`, exported files) next to `evidence.json`.

## Run

```bash
uv run pytest evals/tests/test_parity_m3.py          # offline, FakeLLM, about 3 min (the 100-variant sweep is 70 s)
uv run scriber-parity IN-16 AP-2 ...              # live, once the integrator registers parity_m3.ROWS
```

## Model use

Rows whose acceptance test is about what happens after generation start from a fixture design (`evals/parity/m3/*.json`) answered by `Seeded`, so the live model cannot make them flaky: PR-2, PR-9, PR-10, EX-6, EX-7, AP-1, AP-4, AP-5, CD-2, WP-7, CX-1, CX-6, PF-4. Rows where the model's answer is the thing tested use `rig.llm`: IN-16, AP-2, AP-7, CD-1, WP-6, GE-13, CX-3, and, after a seeded base, IN-17, AP-3, GE-9 (variant plan), PR-7 (suggestions). Offline those get scripted answers, so the live run decides them.

## Rows

| Row | Demo measures | Offline | Live run needs |
|---|---|---|---|
| IN-16 | inputs prompt/sketch.png/plate_spec.md all `used`; params equal to a spec value change when the spec is left out | pass | vision-capable model; the spec must drive params |
| IN-17 | `/api/v1/modify` with a PNG → 202, id in `attachments`, role `used` (image bytes go to the model) | pass | vision model, or Ollama errors on images |
| GE-9 | "Generate 3 versions with 4, 6, 8 ribs" → 3 models, ribs counted by an STL section at 3/4 height; 100-value `length` sweep, 100 valid single solids | pass | model must name `rib_count` and the values |
| GE-13 | 5 prompts × low/high: steps log "thinking low with a 0 token…" vs "high with a 8192 token reasoning budget"; all valid | pass | 10 live generations |
| PR-2 | Base Bolt Spacing X 85→90 via PATCH: centres 90 ±0.01, no LLM call, rebuild p50 375 ms | pass | none |
| PR-7 | suggestions `{target, change, rationale}`; ignore keeps the IR hash and version; accept applies the change | pass (API half) | model must propose valid changes; 3D bubbles are web's |
| PR-9 | 3 edits → 4 versions with prompt and 256 px PNG; restore v1 → params equal | pass | none |
| PR-10 | version `metrics.bbox` 120/80/5 ±0.01, agrees with the exported STEP | pass (API half) | overlay labels are web's |
| EX-6 | unauthenticated share view 200 + GLB, write 401, revoke → 404 | pass (API half) | viewer page is web's |
| EX-7 | stub PLM gets `{model_id, version, files}`, two 503s retried, STEP URL fetches | pass | none |
| AP-1 | Bearer and X-API-Token 200, no token 401, revoked 401 | pass | none |
| AP-2 | `/api/v1/generate` bracket prompt → job id, ≥1 hole, a sloped sketch/datum/taper in the IR and a ≥50 mm² angled planar facet in the STL | pass | the model's design decides |
| AP-3 | `/api/v1/modify` "make it 10 mm thicker" on a 5 mm plate → 15 ±0.01 | pass | the model's update decides |
| AP-4 | `/api/v1/edit` boss_d 30: base part metrics and IR unchanged, only `boss_d` changed, foreign param 400 | pass | none |
| AP-5 | download glb/step/stl: AP214, 1 solid, volume drift 7e-12; watertight, chordal deviation 0.001 mm; Khronos validator 0 errors, node `Plate` | pass | none |
| AP-7 | `/batch` of 10 prompts → 10 jobs done, 10 listed | pass | 10 live generations must build |
| CD-1 | spec span 1000→1100 re-uploaded → regeneration job starts by itself, new span 1100, v1 kept | pass | the model must build the beam (and ideally cite the span fact) |
| CD-2 | versions carry `changes` (params old/new, features added) plus origin and trigger; `change_report.md` rendered | pass | none |
| WP-6 | SSE steps with `progress` 10, 40, 100 then `done` | pass (API half) | progress bar is web's |
| WP-7 | queued → running (held by a gate) → done; failed job; `job_finished` log line with job_id and request_id | pass | none |
| CX-1 | 6 files (PDF, STEP, MD, TXT, CSV, PNG) in one upload → 6 processed, each ingest job streams progress 0 then 100 | pass (API half) | per-file progress UI is web's |
| CX-3 | `context_ids=[a, b]` → version inputs `used` are exactly a, b; their `used_in` shows the model, c's is empty | pass (API half) | "Used in" column is web's |
| CX-6 | stats after 3 uploads and 2 generations match the formula in `docs/agents/context.md` | pass (API half) | UI is web's |
| PF-4 | 10 PATCH edits: rebuild p50 227 ms, max 391 ms; job wall p50 680 ms | pass | reference hardware |

## Product changes made for these rows

- API: `Step.progress` (monotonic by step kind; ingest emits 0 then 100). `Version.inputs` (`prompt` and files with role `used`/`unused`: a file is used when its facts or chunks reached the model or its image was sent). `GenerateIn.thinking` (`low`/`high`). Image attachments (`.png`, `.jpg`) are sent to the model on generate and refine. `context_ids` now include the selected files' facts, like attachments.
- CD-1: replacing a file whose facts changed starts a job per stale model. Parameters citing a changed fact are rebuilt with the new value and the fact as provenance (no LLM); otherwise the model is asked to refine with the change described. Origin `context`, prompt `"<file> changed: <fact> old -> new unit"`. Lineage ids of the replaced document are relinked to the new one, and rebuilds/restores drop lineage ids the context no longer knows (rebuilding after a replace used to crash in `record_generation`).
- GE-9: `POST /models/{id}/variants` with `{instruction}` (the agent's `plan_variants` names one parameter and its values, under the GPU lane) or `{param, values}`; one new model per value, built from the base design without the LLM (origin `variant`).
- PR-7: `POST /models/{id}/suggestions` (agent `suggest` over the design and its findings; changes that fail `apply_params` are dropped), `GET`, `POST …/{sid}/accept` (rebuild, origin `suggestion`), `POST …/{sid}/ignore`. Stored in `models/<id>/suggestions.json`.
- GE-13: `LLM.chat(..., think: int | None)` is a reasoning-token budget (`THINKING_BUDGET` low 0, high 8192). Ollama maps it to `think` on/off and adds it to `num_predict`; Anthropic maps it to effort low/high; FakeLLM records it in `budgets`.
- `Outcome.followups` lets a finished job start others on the event loop; `Jobs.gpu` is public so request-time model calls share the GPU lane.

## Gaps

- `docs/API.md` does not list the new routes and fields yet (integrator).
- Images reach the model, but the default `qwen3.5:4b` must accept images; a text-only model makes IN-16/IN-17 jobs fail.
- CD-1 regenerates only when the replaced file keeps a fact of the same name; a deleted file only marks models stale.
- GE-9's rib count uses a section at 3/4 of the height, which assumes ribs stand on +Z as the prompt asks.
- Suggestions are not tied to a 3D location; the web app shows them by target id.
