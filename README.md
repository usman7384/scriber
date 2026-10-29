# Partwright

An open-source design agent for mechanical CAD. Text, spec files, sketches, drawings, meshes and past designs go in; parametric, editable B-rep parts and assemblies come out. It runs offline on a laptop with local Qwen models (Ollama) and an open kernel (OCCT through build123d).

The model never writes geometry. It writes a typed design IR (`services/ir`) in which every parameter has a name, value, unit, bounds and provenance; the IR compiles deterministically to a build123d script. Every result is built, checked for validity, against the request's dimensions, against project rules and for manufacturability, and repaired before it is returned.

## Layout

| Path | What |
|---|---|
| `services/ir` | design IR, validation, compiler, assemblies, materials |
| `services/geometry` | sandboxed kernel worker, exports (STEP, STL, GLB, IR bundle), DFM, mass, mesh-to-IR, Onshape import/export |
| `services/context` | engineering files to cited facts and rules, project store, retrieval, knowledge graph, sizing and mission adapters |
| `services/agent` | model adapters, generate/refine/repair loop, vision routing, critic, suggestions |
| `apps/api`, `apps/web`, `apps/cli` | HTTP API, React editor, `partwright` command |
| `training` | procedural data generators and the local QLoRA pipeline |
| `evals` | eval cases, harness, parity demos (`partwright-parity`) |

## Quick start

```bash
uv sync
ollama pull qwen3.5:4b
uv run partwright --model qwen3.5:4b generate "mounting bracket, 4x M6 holes, 80x60 plate, 5 mm thick"
uv run partwright serve
```

The default model in `config.yaml`, `partwright-ir:4b-*`, is fine-tuned here and not published; build it with `docs/agents/training.md` or pass `--model qwen3.5:4b`. Images go to `llm.vision` (`qwen3.5:4b`).

## Status

Capability parity is tracked row by row in `docs/reference/PARITY_CHECKLIST.md` and summarised in `docs/PARITY_REPORT.md` (`uv run partwright-parity-report`). A row is done only with a passing acceptance test and a recorded demo (`uv run partwright-parity <rows>`, evidence under `evals/results/`). Decisions are in `docs/DECISIONS.md`, open problems in `docs/KNOWN_ISSUES.md`, the rules for contributors in `AGENTS.md`.

Apache-2.0.
