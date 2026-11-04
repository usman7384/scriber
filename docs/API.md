# HTTP API contract (M3)

Shared by `apps/api` (FastAPI) and `apps/web` (React). JSON unless stated. All ids are opaque strings. Times are ISO 8601 UTC. Lengths are mm, angles deg. The OpenAPI document served at `/openapi.json` is the source of truth once it exists; this file is the starting contract and changes only through the integrator.

## Auth

Local single-user mode (default): no auth on `127.0.0.1`. When `api.auth: tokens` is configured, every request except `GET /health` and share links needs `Authorization: Bearer <token>` or `X-API-Token: <token>`; 401 otherwise. Tokens: `POST /tokens {name} -> {id, name, token, created}` (token shown once), `GET /tokens`, `DELETE /tokens/{id}`.

## Resources

```
Project  {id, name, created, model_count, file_count}
File     {id, project_id, name, kind, role, status: "processing"|"processed"|"failed", error?, facts, rules, uploaded, used_in: [model_id]}
Fact     {id, file_id, kind, name, value, unit, tol?, count?, page, line, text, ref}
Rule     {id, kind, value, unit, process, severity, binding, text, source_ref?}
Model    {id, project_id, title, created, latest_version, versions: int, thumbnail_url?}
Version  {model_id, number, created, status: "ok"|"failed", origin: "generate"|"refine"|"edit"|"params"|"restore", prompt?, params: [Param], checks: [Check], findings: [Finding], metrics: {bbox, volume, mass_g?, holes}, files: {step, stl, glb, py, ir} (URLs), thumbnail_url}
Param    {name, label, value, unit, min?, max?, description, provenance: {source, ref?, quote?}}
Check    {description, passed, actual}
Finding  {rule_id, severity, binding, message, part?, measured?, required?, location?: {point, face}, suggestion?}
Job      {id, kind: "generate"|"refine"|"edit"|"params"|"ingest"|"batch", status: "queued"|"running"|"done"|"failed", project_id, model_id?, version?, error?, created, started?, finished?, steps: [Step]}
Step     {kind, message, attempt, elapsed_ms, thumbnail_url?}
GraphView {nodes: [{id, type, name}], edges: [{src, dst, type}], counts}
KbStats  {files, facts, rules, entities, relations, generations, used_in_generation, score, level, next_level_score}
```

## Routes

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | /health | | {status, model, ollama: bool, tools: {freecad: bool, prusaslicer: bool}} |
| POST | /projects | {name} | Project |
| GET | /projects | | [Project] |
| GET | /projects/{id} | | Project |
| POST | /projects/{id}/context | multipart `files[]` | [Job] (one ingest job per file) |
| GET | /projects/{id}/context | | {files: [File], stats: KbStats} |
| GET | /projects/{id}/context/{file_id}/facts | | [Fact] |
| DELETE | /projects/{id}/context/{file_id} | | 204 |
| GET | /projects/{id}/rules | | [Rule] |
| PUT | /projects/{id}/rules/{rule_id} | Rule | Rule |
| GET | /projects/{id}/graph | | GraphView |
| POST | /projects/{id}/generate | {prompt, process?: Process, context_ids?: [file_id], attachments?: [file_id], thinking?: low\|high} | Job |
| GET | /projects/{id}/models | | [Model] |
| GET | /models/{id} | | Model + latest Version |
| GET | /models/{id}/versions | | [Version] |
| GET | /models/{id}/versions/{n} | | Version |
| POST | /models/{id}/versions/{n}/restore | | Version (new number) |
| POST | /models/{id}/refine | {instruction, target?: part_id, process?} | Job |
| PATCH | /models/{id}/params | {values: {name: number}} | Job (fast path: no LLM) |
| POST | /models/{id}/variants | {instruction} or {param, values: [number]} | [Job], one new model per value (origin `variant`) |
| POST | /models/{id}/suggestions | | [Suggestion {id, target, change, rationale}] |
| GET | /models/{id}/suggestions | | [Suggestion] |
| POST | /models/{id}/suggestions/{sid}/accept | | Job (rebuild, origin `suggestion`) |
| POST | /models/{id}/suggestions/{sid}/ignore | | Suggestion |
| GET | /models/{id}/export?fmt=step\|stl\|glb\|py\|ir\|fcstd&version=n | | file; `fcstd` is a FreeCAD PartDesign document written by FreeCAD (422 naming the construct it cannot map, 503 when FreeCAD is not configured) |
| POST | /models/{id}/slice?version=n | | {model_id, version, ok, exit_code, manifold, layers, gcode_bytes, warnings, errors}: PrusaSlicer printability of the version's STL (503 when PrusaSlicer is not configured) |
| GET | /models/{id}/components?version=n | | [Component]: part id, name, material, parent part and joint |
| POST | /models/{id}/face-driver | {point: [x,y,z], normal: [x,y,z], version?} | {part, feature, param, rate}: the parameter that moves the picked planar face; 404 when none does |
| GET | /projects/{id}/jobs?active=true | | [Job] newest first; `active` keeps queued and running |
| GET | /jobs/{id} | | Job |
| GET | /jobs/{id}/events | | SSE: `event: step` data Step; `event: done` data Job; `event: failed` data Job |
| POST | /batch | {project_id, prompts: [string], process?} | {jobs: [Job]} |
| POST | /shares | {model_id, version?} | {id, url} |
| GET | /s/{share_id} | | read-only Model + Version (no auth) |
| DELETE | /shares/{id} | | 204 |
| POST | /hooks | {url, events: ["version.created", "job.failed"]} | {id, url, events} |
| DELETE | /hooks/{id} | | 204 |
| POST | /projects/{id}/designs | {design: Design IR, prompt?} | Job (kind `build`, origin `design`; no LLM; 400 on IR errors) |
| POST | /projects/{id}/sizing?name=sizing.xml | raw sizing XML (D-031 `XmlSizing`) | Job (kind `build`, origin `sizing`; no LLM; 400 on a bad file) |
| GET | /materials?q=text | | [Material {name, density_g_cm3, youngs_modulus_gpa, yield_mpa, source}] (all, or the best match) |
| PUT | /models/{id}/material | {material, part?} | Job (rebuild with the material on that part or all parts, origin `material`; 400 when unknown) |
| GET | /models/{id}/sensitivities?version=n&params=a&params=b | | {model_id, version, metrics, params: [{name, value, unit, step, d: {volume, mass_g, bbox_x, bbox_y, bbox_z}, error?}]} |
| POST | /models/{id}/simulation | {solver?, load_case?, results: [{face_group, max_stress_mpa, allowable_mpa}]} | [Suggestion] for the groups over the limit ([] when none); accept with the suggestion route |
| POST | /bugs | {model_id, version, text, screenshot?: data URL (PNG/JPEG)} | 201 Bug {id, model_id, version, text, user, created, screenshot_url} |
| GET | /bugs?model_id= | | [Bug] |
| GET | /bugs/{id}/screenshot | | image |
| GET | /usage | | {user, generations, limit} |
| POST | /community | {model_id, version?} | 201 Publication {id, model_id, version, title, author, created, thumbnail_url} |
| GET | /community | | [Publication] newest first, every user |
| GET | /community/{id} | | Publication |
| DELETE | /community/{id} | | 204 (author only, else 403) |
| POST | /community/{id}/fork | {project_id} | 201 Model + Version: an editable copy, `forked_from {publication, model_id, version, title, author}`, origin `fork` |

Process = `any | milling_3axis | fdm | sla | sls`.

## Reference-compatible aliases

Under `/api/v1`, with the same token auth: `POST /api/v1/generate {prompt, image?, mesh?}`, `POST /api/v1/modify {model_id, prompt}`, `POST /api/v1/edit {model_id, component_id, params}`, `POST /api/v1/download {model_id, format: glb|step|stl}`. Each returns `{job_id}` or the file; they map onto the routes above in a default project.

## Behaviour

- One GPU job runs at a time (generate, refine, edit); ingest and params jobs run beside it. Jobs survive an API restart as `failed` with error "interrupted".
- `PATCH /models/{id}/params` rebuilds without the LLM and should finish in about a second for small parts once the CAD worker is warm.
- Successful versions are recorded in the project knowledge graph. A context file change that makes models stale emits `version.stale` on hooks and starts a regeneration job per stale model: parameters that cite the changed fact take the new value without the LLM, otherwise the model refines the design with the change described (circular design).
- `face-driver` matches the picked point (CAD mm) and outward normal against the cap planes of extrudes sketched on XY/XZ/YZ or an unrotated datum, within 0.01 mm. `rate` is mm the face moves along its normal per unit of `param`, so offsetting the face by `t` mm sets `param += t / rate`. Faces of parts placed by a joint, side walls and faces of other features have no driver yet.
- `Step.progress` is a percentage, monotonic per job. `Version.inputs` lists the prompt and each file with role `used` or `unused`. PNG and JPG attachments are sent to the model as images on generate and refine; `context_ids` pass the selected files' facts.
- Users: with `auth: tokens` a user is the token's name (two tokens with one name are one user); without auth every request is user `local`. Projects and models are not user-scoped; the community listing is the shared space.
- Generation limit: `generation_limit` in the API settings (default unset, unlimited) caps generate, refine, batch, `/api/v1/generate` and `/api/v1/modify` requests per user; past it they return 429. A batch is charged per prompt, all or nothing. Context-triggered regenerations are not charged.
- Sensitivities are central finite differences (step 1e-3 of the value, at least 1e-3 mm or deg, one-sided at a bound) over `mm` and `deg` parameters, each a kernel rebuild without exports; mass needs a material on every part.
- External tools: `freecad` and `prusaslicer` in the API settings are executable paths (`scriber serve` reads `SCRIBER_FREECAD` and `SCRIBER_PRUSASLICER`; unset means the tool is off and `/health` says so). They run as subprocesses off the event loop; see `docs/INTEROP.md#external-tools`. The FCStd export is written per request, not stored; slicing uses PrusaSlicer's built-in defaults and discards the G-code after counting.
- Errors: `{"detail": "..."}` with 400 (bad input), 403 (not yours), 404, 409 (job still running), 422 (validation, or no FreeCAD mapping for the design), 429 (generation limit), 502 (FreeCAD or PrusaSlicer failed), 503 (Ollama unreachable, or the tool not configured).
