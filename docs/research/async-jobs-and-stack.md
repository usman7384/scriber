# Async jobs, observability, streaming, frontend, thumbnails

Researched 2026-10-25. Versions are the latest on PyPI/npm today (verified via `uv pip compile` / `npm view`).

## TL;DR

- **Jobs: an in-process asyncio dispatcher plus a SQLite job table (`aiosqlite` 0.22.1), executing CAD and LLM steps in subprocess workers.** No Redis and no broker. It runs identically on Windows and Linux.
- **Progress: SSE** (`sse-starlette` 3.5.1) with `Last-Event-ID` resume, backed by the job-events table.
- **Observability: structlog 26.1.0** (JSON to file, pretty console) with `job_id`/`project_id` contextvars. **OpenTelemetry SDK 1.45.1** is optional and off by default (offline); there is an OTLP exporter only if the user configures an endpoint.
- **Frontend: Vite 8.3.5 + React 19.3.1 + TypeScript + three 0.186.1 + @react-three/fiber 9.8.2 + @react-three/drei 10.7.9** (all MIT), plus TanStack Query 5 and zustand 5.
- **Thumbnails: trimesh 5.2.0 + pyrender 0.1.45** offscreen. **Verified on Windows:** a GLB → 256×256 PNG in 0.65 s through pyglet's hidden-window GL context. On headless Linux/Docker, use `PYOPENGL_PLATFORM=egl` (NVIDIA) or `osmesa`.

## Job system options

| | In-process asyncio + SQLite | huey 3.5.3 (SqliteHuey) | arq 0.28.0 | Celery 5.6.3 | RQ 2.12.0 |
|---|---|---|---|---|---|
| Broker | none (SQLite file) | SQLite file | **Redis** | Redis/RabbitMQ | **Redis** |
| Windows | yes | yes (thread/process workers; not verified) | needs Redis (no native Redis build; Memurai or WSL/Docker) | **not officially supported**; `--pool=solo` workaround | **no**: needs `fork()`, so WSL only |
| Status | ours | active | **maintenance-only mode** (PyPI description, verified) | active | active |
| Async-native | yes | no | yes | no | no |
| Fit for a single-user, local-first app with a single GPU | **best** | good fallback if we want a separate worker process | no | overkill | no |

Redis on Windows: there is still no official native build. Redis's recommended Windows path is the commercial Memurai port ([redis.io](https://redis.io/tutorials/howtos/how-to-run-redis-on-windows-natively-with-memurai.md)), which is one more reason to avoid Redis-based queues.

### Design

```
FastAPI (uvicorn 0.54, fastapi 0.162)
 ├─ POST /jobs → INSERT jobs(status=queued) → dispatcher.notify()
 ├─ GET /jobs/{id}/events (SSE) → tail job_events (id, job_id, seq, type, payload)
 └─ dispatcher (asyncio task, started in lifespan)
      resources: Semaphore gpu=1, cpu=max(1, cores-4)=4, io=8
      step runner:  LLM steps → async HTTP to Ollama (gpu sem)
                    CAD compile / DFM / export / thumbnail → subprocess worker (cpu sem)
                         ProcessPool of 1–2 *warm* workers (build123d import costs 12–15 s cold, verified)
                         hard timeout per step (e.g. 120 s) → kill & restart worker (OCCT can hang/segfault)
      crash recovery: on startup, jobs in status=running → requeue (idempotent steps, checkpoint per step)
```

- Use SQLite in WAL mode, one writer (the dispatcher), with short transactions.
- Cancellation: a `cancel_requested` flag is checked between steps. Kill the subprocess for CAD steps. Cancel the HTTP stream for Ollama.
- **Why subprocesses:** OCCT is C++, so a bad boolean or fillet can segfault and take the API down. A thread cannot be killed. Warm workers amortise the import cost.

## Progress streaming: SSE vs WebSocket

| | SSE | WebSocket |
|---|---|---|
| Direction | server → client (enough for job progress and token streaming) | bidirectional |
| Resume | built-in `Last-Event-ID`, which we map to `job_events.seq` | manual |
| Proxies / infra | plain HTTP; works through anything | upgrade handling needed |
| Choice | **default** | only later, for collaborative editing or live viewport sync |

## Observability

- `structlog` with processors: timestamp, level, `contextvars` (`project_id`, `job_id`, `step`), and a JSON renderer to `logs/app.jsonl`. Rotate daily and keep 7 days.
- Per-step metrics are stored in the job table: duration, tokens in/out, tok/s, VRAM (from `ollama ps`), retries and validation errors. This feeds the eval harness and the UI's job details.
- OpenTelemetry: `opentelemetry-instrumentation-fastapi` 0.66b1, enabled only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. Never phone home by default.

## Frontend

| Package | Version | Licence | Role |
|---|---|---|---|
| vite | 8.3.5 | MIT | dev server/build |
| react | 19.3.1 | MIT | UI |
| typescript | 7.0.2 | Apache-2.0 | types (TS 7 is the native Go compiler; if tooling lags, pin 5.9.x, not checked) |
| three | 0.186.1 | MIT | rendering |
| @react-three/fiber | 9.8.2 | MIT | React renderer for three (v9 targets React 19) |
| @react-three/drei | 10.7.9 | MIT | `useGLTF`, `Bounds`, `OrbitControls`, `Edges`, `GizmoHelper` |
| @tanstack/react-query | 5.104.5 | MIT | API cache |
| zustand | 5.0.16 | MIT | UI state |
| three-cad-viewer | 5.1.3 | MIT | optional: a CAD-style viewer (tree, clipping, measuring) from the ocp_vscode author |
| occt-import-js / opencascade.js | 0.0.23 / 1.1.1 | **LGPL-2.1** | avoid by default (WASM, large); the backend already converts STEP → GLB |

- GLB is the viewer format. Keep per-part nodes named by IR part id and per-face groups, so DFM highlights and selection map back to the IR.
- glTF is Y-up while CAD is Z-up. Rotate −90° about X on export or in the viewer. The verified thumbnail came out rotated because of this.

## Headless thumbnails

| Option | Windows | Headless Linux | Deps | Verdict |
|---|---|---|---|---|
| **pyrender + trimesh** | **verified** (0.65 s, 256²) | EGL/OSMesa via `PYOPENGL_PLATFORM` | pyrender pins `pyopengl==3.1.0` (built from sdist); pyglet 2.1 | **default** |
| VTK offscreen | yes | yes (OSMesa/EGL wheels) | `vtk` ~78 MB wheel (only needed if we used CadQuery) | fallback |
| three.js headless (Puppeteer) | yes | yes | Chromium (~150 MB+) | no (heavy) |
| Client-side `canvas.toBlob()` uploaded after the first view | yes | n/a | none | complement: a free, higher-quality thumbnail when the UI is open |
| OCCT `V3d` offscreen | possible | needs GL | already present | no (low-level, poor API) |

Pin `pyrender==0.1.45`, `trimesh==5.2.0`, `pyglet<3`. pyrender is old and barely maintained, so keep the renderer behind a small `render_thumbnail(glb) -> png` interface.
