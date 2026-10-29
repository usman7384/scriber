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
| GET | /health | | {status, model, ollama: bool} |
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
| POST | /models/{id}/suggestions/{sid}/ignore | | 204 |
| GET | /models/{id}/export?fmt=step\|stl\|glb\|py\|ir&version=n | | file |
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

Process = `any | milling_3axis | fdm | sla | sls`.

## Reference-compatible aliases

Under `/api/v1`, with the same token auth: `POST /api/v1/generate {prompt, image?, mesh?}`, `POST /api/v1/modify {model_id, prompt}`, `POST /api/v1/edit {model_id, component_id, params}`, `POST /api/v1/download {model_id, format: glb|step|stl}`. Each returns `{job_id}` or the file; they map onto the routes above in a default project.

## Behaviour

- One GPU job runs at a time (generate, refine, edit); ingest and params jobs run beside it. Jobs survive an API restart as `failed` with error "interrupted".
- `PATCH /models/{id}/params` rebuilds without the LLM and should finish in about a second for small parts once the CAD worker is warm.
- Successful versions are recorded in the project knowledge graph. A context file change that makes models stale emits `version.stale` on hooks and starts a regeneration job per stale model: parameters that cite the changed fact take the new value without the LLM, otherwise the model refines the design with the change described (circular design).
- `face-driver` matches the picked point (CAD mm) and outward normal against the cap planes of extrudes sketched on XY/XZ/YZ or an unrotated datum, within 0.01 mm. `rate` is mm the face moves along its normal per unit of `param`, so offsetting the face by `t` mm sets `param += t / rate`. Faces of parts placed by a joint, side walls and faces of other features have no driver yet.
- `Step.progress` is a percentage, monotonic per job. `Version.inputs` lists the prompt and each file with role `used` or `unused`. PNG and JPG attachments are sent to the model as images on generate and refine; `context_ids` pass the selected files' facts.
- Errors: `{"detail": "..."}` with 400 (bad input), 404, 409 (job still running), 422 (validation), 503 (Ollama unreachable).
