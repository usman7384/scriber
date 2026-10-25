# Technical research summary: decided recommendations

2026-10-25. Details and sources are in the sibling files. **Verified** means it was run on this machine today.

## Stack decisions (pinned)

| Area | Decision | Pin | Notes |
|---|---|---|---|
| Python | CPython **3.12** (uv-managed) | 3.12.x | Needed for `planegcs` wheels (cp312+). build123d supports 3.11–3.14 |
| CAD kernel lib | **build123d** on OCP/OCCT 8.0.1 (no VTK) | `build123d==0.13.0` (→ `cadquery-ocp-novtk==8.0.1.1.0`) | **Verified** headless on Windows: box+hole, STEP (names, colours, hierarchy), STL, GLB, STEP re-import. **Never co-install CadQuery 2.8** (OCP 7.9 vs 8.0 clash, verified broken) |
| Sketch solver | PlaneGCS bindings | `planegcs==0.9.6` | LGPL-2.1+, imported dynamically |
| Standard parts | bd_warehouse | `bd_warehouse==0.4.0` | Apache-2.0. ISO 4762, ISO 4032/4033/4035, clearance/tap/drill tables, bearings, threads (**verified**) |
| Feature-tree hand-off | STEP AP214 (AP242 option) + IR JSON + generated `.py`; FreeCAD `.FCStd` replay (optional subprocess) | FreeCAD 1.1 (optional) | STEP never carries history |
| Inference runtime | **Ollama** (native Windows) | 0.40.11 | vLLM only via WSL, later, optional |
| Structured output | Ollama `format` = JSON schema from Pydantic, `temperature 0`, `think:false`, staged generation, Pydantic re-validation + repair loop (≤2) | `pydantic==2.14.1`, `ollama==0.6.3` | Schema conformance **verified** on 7B; semantics still need few-shot and validators |
| Default IR + vision model | **`qwen3.5:4b`** (q4_K_M, multimodal, Apache-2.0), `num_ctx 16384` | 3.3–4.0 GB | One model for IR and vision, so no swaps. Only 8 of 32 layers keep KV (config verified) |
| IR A/B model | `qwen2.5-coder:7b-instruct-q4_K_M`, `num_ctx 8192` | 4.7 GB (present) | **Verified**: 5.0 GB, 100% GPU, 15.2 tok/s generation, 405 tok/s prompt |
| Vision fallback | `qwen3-vl:4b-instruct` (pull only if needed) | 3.3 GB | |
| Embeddings | `qwen3-embedding:0.6b` | 639 MB | Apache-2.0, 32k context |
| CI model | `qwen3.5:0.8b-q8_0` (+ mock LLM, hash embedder) | 1.0 GB | Same template and vision path as the default |
| Doc parsing | `pypdfium2==5.14.0`, `pdfplumber==0.11.10`, `camelot-py==2.0.0`, `python-docx==1.2.0`, `pint==0.25.3` (verified); optional extra `docling==2.142.1` | | **No PyMuPDF (AGPL), no marker (weights licence)** |
| OCR / CV | `rapidocr==3.10.0`, `opencv-python-headless==5.0.0.93` | | PaddleOCR/Tesseract optional |
| Graph store | SQLite property graph + `networkx==3.6.1` | | Kùzu archived (Oct 2025). LadybugDB fork: `real-ladybug` 0.15.3 works, `ladybug` 0.22.0 fails on Windows (both verified). Revisit later |
| Vector store | `sqlite-vec==0.1.9` + FTS5 hybrid, in the same project DB | | **Verified** on Windows |
| Job system | In-process asyncio dispatcher + SQLite (`aiosqlite==0.22.1`) + warm subprocess CAD workers with timeouts; GPU semaphore = 1 | | No Redis. arq is maintenance-only, RQ needs fork, Celery has no Windows support |
| API / streaming | `fastapi==0.162.0`, `uvicorn==0.54.0`, SSE via `sse-starlette==3.5.1` | | |
| Logging / tracing | `structlog==26.1.0`; `opentelemetry-sdk==1.45.1` opt-in | | Offline by default |
| Frontend | Vite 8.3.5, React 19.3.1, TS 7.0.2 (fall back to 5.9 if tooling lags), three 0.186.1, @react-three/fiber 9.8.2, drei 10.7.9 | | All MIT/Apache |
| Thumbnails | `trimesh==5.2.0` + `pyrender==0.1.45` offscreen (EGL/OSMesa on Linux) | | **Verified** on Windows, 0.65 s for 256² |
| Fine-tune | Unsloth 2026.10.8 in WSL2; toy = Qwen2.5-Coder-1.5B LoRA; next = Qwen3.5-0.8B bf16 LoRA; merge → GGUF Q4_K_M → `ollama create` | trl 1.16.0, peft 0.21.2 | 7B QLoRA is not practical on 6 GB |
| Project licence | **Apache-2.0** | | See conflicts below |

## Licence check (Apache-2.0 project)

- **OK with conditions:** OCCT (LGPL-2.1 + OCCT exception) and planegcs (LGPL-2.1+). Use them only as dynamically loaded wheels, never vendored or statically linked, and include the LGPL notice and attribution in NOTICE. FreeCAD (LGPL) is used only as an optional external subprocess.
- **Excluded (copyleft or restricted):** PyMuPDF (AGPL-3.0), marker weights (Open RAIL-M with a revenue cap), python-solvespace/py-slvs (GPL-3), FreeCAD Fasteners WB (GPL-2), BOLTS (GPL/LGPL), CADAM code (GPL-3), Neo4j Community server (GPL-3), occt-import-js/opencascade.js (LGPL, awkward in a JS bundle).
- **Models:** all selected models are Apache-2.0 (verified on HF). **Avoid Qwen2.5-Coder-3B and Qwen2.5-VL-3B** (Qwen Research Licence, non-commercial, verified).
- **Datasets:** Fusion 360 Gallery, Text2CAD (CC BY-NC-SA), CAD-Recode (CC BY-NC) and Point2CAD code (CC BY-NC) may be used for eval only. Weights we publish must be trained on our procedural corpus plus permissive sets (CAD-Coder-text, Apache-2.0 per HF metadata).

## Risks on this hardware

1. **Disk is critical.** ~14 GB free on each of C: and D:. Ollama models live on C:. The HF cache on C: is 55 GB and the uv cache ~9 GB; reclaiming them is the user's call. Point `OLLAMA_MODELS` at D: before large new pulls.
2. **VRAM headroom ~1 GB.** 4B (16k) + embedder ≈ 5.2 GB. Any spill to CPU is 5–10× slower. Serialise GPU work, cap `num_ctx`, fall back to CPU embeddings.
3. **Throughput.** 15 tok/s on the 7B means ~100 s per 1.5k-token IR. Use staged, smaller schemas and prefer the 4B.
4. **Unverified:** Qwen3.5-4B IR quality and how `think` interacts with `format` on Ollama 0.40.11. Day 1 of M1 is the eval harness and an A/B against the 7B.
5. **OCCT stability.** Crashes/hangs on booleans and fillets; 12–15 s cold import (verified). Subprocess isolation, timeouts, warm workers.
6. **New kernel line.** OCP 8.0 is weeks old. Pin it and run golden-geometry tests.
7. **RAM 16 GB.** Ollama + CAD worker + optional docling (~2–3 GB) + browser + Vite. Keep docling off by default. The WSL 8 GB cap matters for fine-tuning.
8. **Laptop thermal throttling** (±30 % on long jobs).

## Expected disk footprint

| Item | Size |
|---|---|
| Ollama models, new: `qwen3.5:4b` 3.3–4.0 + `qwen3-embedding:0.6b` 0.64 + `qwen3.5:0.8b-q8_0` 1.0 | ≈ 5.0–5.6 GB |
| Ollama existing: `qwen2.5-coder:7b` (the alias shares blobs) | 4.7 GB (present) |
| Backend venv (build123d novtk 0.54 GB + API, parsers, OCR, CV, render) | ≈ 1.0 GB (estimate) |
| Frontend `node_modules` | ≈ 0.3–0.4 GB |
| **Core new total** | **≈ 6.5–7 GB** |
| Optional: docling / FreeCAD / fine-tune WSL env (peak) / `qwen3-vl:4b` | +1.5–2 / +1 / +8–12 / +3.3 GB |

## Not verified

Qwen3.5-4B IR quality; any VLM run on sketches; fine-tune VRAM/run-time numbers (published figures); AP242 export; FreeCAD headless emitter; bd_warehouse clearance table vs ISO 273; vLLM in WSL; licences of CADPrompt, BenchCAD and image CAD-Coder; competitor pricing (aggregators).
