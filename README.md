# Scriber

An open-source design agent for mechanical CAD. Text, spec files, sketches, drawings, meshes and past designs go in; parametric, editable B-rep parts and assemblies come out. It runs offline on a laptop with local Qwen models (Ollama) and an open kernel (OCCT through build123d).

The model never writes geometry. It writes a typed design IR (`services/ir`) in which every parameter has a name, value, unit, bounds and provenance; the IR compiles deterministically to a build123d script. Every result is built, checked for validity, against the request's dimensions, against project rules and for manufacturability, and repaired before it is returned.

## Layout

| Path | What |
|---|---|
| `services/ir` | design IR, validation, compiler, assemblies, materials |
| `services/geometry` | sandboxed kernel worker, exports (STEP, STL, GLB, IR bundle), DFM, mass, mesh-to-IR, Onshape import/export |
| `services/context` | engineering files to cited facts and rules, project store, retrieval, knowledge graph, sizing and mission adapters |
| `services/agent` | model adapters, generate/refine/repair loop, vision routing, critic, suggestions |
| `apps/api`, `apps/web`, `apps/cli` | HTTP API, React editor, `scriber` command |
| `training` | procedural data generators and the local QLoRA pipeline |
| `evals` | eval cases, harness, parity demos (`scriber-parity`) |

## Quick start

Needs Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 22, [Ollama](https://ollama.com) and about 6 GB of GPU memory for the 4B models (CPU works, slowly).

```bash
uv sync
ollama pull qwen3.5:4b
ollama pull qwen3-embedding:0.6b
uv run scriber --model qwen3.5:4b generate "mounting bracket, 4x M6 holes, 80x60 plate, 5 mm thick"
```

The API and the web editor:

```bash
uv run scriber --model qwen3.5:4b serve
npm ci --prefix apps/web
npm run dev --prefix apps/web
```

The API listens on `http://127.0.0.1:8000`, the editor on `http://127.0.0.1:5173`. Outputs go to `out/`, projects and models to `data/`.

The default model in `config.yaml`, `scriber-ir:4b-s3`, is a fine-tune of `qwen3.5:4b` published at [usman7384/scriber-ir-4b-s3-GGUF](https://huggingface.co/usman7384/scriber-ir-4b-s3-GGUF):

```bash
hf download usman7384/scriber-ir-4b-s3-GGUF --local-dir scriber-ir-4b-s3
cd scriber-ir-4b-s3 && ollama create scriber-ir:4b-s3 -f Modelfile
```

With it installed, drop `--model qwen3.5:4b` from the commands above. `docs/agents/training.md` has the steps to rebuild it. Requests with images go to `llm.vision` (`qwen3.5:4b`).

## Checks

The steps in `.github/workflows/ci.yml`: `ruff`, `mypy`, `lint-imports` and `pytest -m "not llm"` for Python; `npm run lint`, `typecheck`, `test`, `e2e` and `parity` in `apps/web`. The `llm` tests need Ollama with `qwen3.5:0.8b-q8_0`.

## Status

Capability parity is tracked row by row in `docs/reference/PARITY_CHECKLIST.md` and summarised in `docs/PARITY_REPORT.md` (`uv run scriber-parity-report`). A row is done only with a passing acceptance test and a recorded demo (`uv run scriber-parity <rows>`, evidence under `evals/results/`). Decisions are in `docs/DECISIONS.md`, open problems in `docs/KNOWN_ISSUES.md`, the rules for contributors in `AGENTS.md`.

## Licence

Apache-2.0, see `LICENSE`.
