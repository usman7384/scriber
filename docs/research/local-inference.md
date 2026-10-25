# Local inference on a 6 GB RTX 3060 Laptop

Researched 2026-10-25. Sizes are from the Ollama library tag pages, fetched today. Licences are from Hugging Face API model metadata (verified today).

## TL;DR

| Role | Pick | Ollama tag | Download | Why |
|---|---|---|---|---|
| Default reasoning / IR emitter **and** vision | **Qwen3.5-4B** (Mar 2026, Apache-2.0) | `qwen3.5:4b` (q4_K_M; text and vision in one model) | 3.3–4.0 GB | Natively multimodal, so there is no model swap between the IR and sketch/vision-critique steps. Hybrid Gated-DeltaNet attention: only 8 of 32 layers keep a KV cache, so 16–32k context is cheap. Vendor claims it beats Qwen3-VL on reasoning, coding and vision |
| IR fallback / A-B (already on disk) | Qwen2.5-Coder-7B-Instruct | `qwen2.5-coder:7b-instruct-q4_K_M` | 4.7 GB (present) | The strongest code-specialist that fits. Verified to run 100% on GPU at 8k context. Text only |
| Vision fallback (only if 3.5-4B vision disappoints) | Qwen3-VL-4B-Instruct | `qwen3-vl:4b-instruct` | 3.3 GB | Apache-2.0 and 256K context. Pull only on demand |
| Embeddings | Qwen3-Embedding-0.6B | `qwen3-embedding:0.6b` | 639 MB | Apache-2.0, 32K context, multilingual, top MTEB for its size. Can stay co-resident with the 4B model |
| CI / tests | Qwen3.5-0.8B | `qwen3.5:0.8b-q8_0` | 1.0 GB | Same family, chat template and vision path as the default, so CI exercises the image path too. CPU-runnable |
| Runtime | **Ollama 0.40.11** (native Windows) | — | — | Already installed. JSON-schema `format` **verified**. vLLM stays an optional WSL backend |

**Context defaults** (`num_ctx`): 16384 for `qwen3.5:4b` (headroom to 32768); 8192 for the 7B coder (12288 maximum with a q8_0 KV cache). Set `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_MAX_LOADED_MODELS=2` (LLM + embedder) and `OLLAMA_KEEP_ALIVE=10m`.

**Decision D-002 should be revised** from "7B–8B default" to "Qwen3.5-4B default, 7B coder as A/B", subject to the M1 eval harness. If the eval shows the 7B coder clearly ahead on IR validity, swap the default. That costs no extra disk.

## Measured on this machine (verified)

- `ollama ps` with the 7B coder at 8k context: **5.0 GB, 100% GPU**, llama.cpp runner. `nvidia-smi` shows 4.9 / 6.1 GiB used, so about 1.1 GiB is free.
- A structured-output request (`/api/chat` with `format` = JSON schema using enums, `additionalProperties:false` and required arrays) returned **schema-valid JSON**. Generation ran at **15.2 tok/s** and prompt processing at **405 tok/s** (7B q4_K_M).
- Semantics were poor even though the schema held: the model invented chamfers and emitted the hole as a separate "part". The schema guarantees shape, not meaning. We still need few-shot examples, a schema description in the prompt, a semantic validator and the repair loop.
- Expect roughly 100 s for a 1.5k-token IR on the 7B. The 4B model should be about 1.6–2× faster (estimate; measure in M1).

## Fit table (6 GB VRAM; KV cache fp16 unless noted)

KV bytes per token = 2 × (layers with attention) × KV heads × head_dim × 2 B.

| Model | Ollama tag | Weights | KV / token | Fits at | Licence | Verdict |
|---|---|---|---|---|---|---|
| Qwen2.5-Coder-0.5B | `qwen2.5-coder:0.5b` | 398 MB | 12 KB | 32k | Apache-2.0 | tests only |
| Qwen2.5-Coder-1.5B | `qwen2.5-coder:1.5b` | 986 MB | 28 KB | 32k | Apache-2.0 | fine-tune base |
| Qwen2.5-Coder-3B | `qwen2.5-coder:3b` | 1.9 GB | 36 KB | 32k | **Qwen Research Licence (non-commercial)**, verified | **avoid** |
| Qwen2.5-Coder-7B | `qwen2.5-coder:7b-instruct-q4_K_M` | 4.7 GB | 56 KB | 8k (12k with q8 KV) | Apache-2.0 | A/B IR model (present) |
| Qwen2.5-Coder-14B | `qwen2.5-coder:14b` | 9.0 GB | — | no (CPU offload, ~3–5 tok/s) | Apache-2.0 | no |
| Qwen3-1.7B | `qwen3:1.7b` | 1.4 GB | 112 KB | 16k | Apache-2.0 | superseded by 3.5 |
| Qwen3-4B-Instruct-2507 | `qwen3:4b-instruct-2507-q4_K_M` | 2.5 GB | 144 KB | 16k | Apache-2.0 | text-only alternative |
| Qwen3-8B | `qwen3:8b` | 5.2 GB | 144 KB | ~2–4k only | Apache-2.0 | no (context too small) |
| Qwen3-14B | `qwen3:14b` | 9.3 GB | — | no | Apache-2.0 | no |
| **Qwen3.5-0.8B** | `qwen3.5:0.8b-q8_0` | 1.0 GB | small | 32k+ | Apache-2.0 | CI |
| Qwen3.5-2B | `qwen3.5:2b-q4_K_M` | 1.9 GB | small | 32k+ | Apache-2.0 | low-VRAM fallback |
| **Qwen3.5-4B** | `qwen3.5:4b` (q4_K_M 3.3 GB) | 3.3–4.0 GB | **32 KB** (8 full-attention layers × 4 KV × 256; config verified) | 32k (~5 GB); 16k ≈ 4.5 GB (estimate) | Apache-2.0 | **default** |
| Qwen3.5-9B | `qwen3.5:9b-q4_K_M` | 6.6 GB | — | no (partial offload) | Apache-2.0 | only with ≥8 GB VRAM |
| Qwen3-Coder | `qwen3-coder:30b` (smallest) | 19 GB | — | no | Apache-2.0 | **no small Qwen3-Coder exists** |
| Qwen2.5-VL-3B | `qwen2.5vl:3b` | 3.2 GB | — | 8k | **Qwen Research Licence**, verified | avoid |
| Qwen2.5-VL-7B | `qwen2.5vl:7b` | 6.0 GB | — | no | Apache-2.0 | no |
| Qwen3-VL-2B / 4B / 8B | `qwen3-vl:2b` / `4b` / `8b` | 1.9 / 3.3 / 6.2 GB | 144 KB (4B) | 4B: 8k | Apache-2.0 | 4B as vision fallback |
| Qwen3-Embedding-0.6B | `qwen3-embedding:0.6b` | 639 MB | — | — | Apache-2.0 | **embeddings** |
| bge-m3 | `bge-m3` | ~1.2 GB | — | — | MIT | alternative (dense + sparse) |
| nomic-embed-text v1.5 | `nomic-embed-text` | ~274 MB | — | — | Apache-2.0 | lightweight alternative (2k context) |
| all-MiniLM-L6-v2 | HF cache | 90 MB | — | — | Apache-2.0 | unit tests on CPU |

Newer families seen on ollama.com (`qwen3.6` 27B/35B, `qwen3.8` 27B, `qwen3-coder-next`) are all ≥27B, so none of them fit.

## Runtimes

| | Ollama 0.40.11 | llama.cpp (`llama-server`) | vLLM 0.32.0 |
|---|---|---|---|
| Windows | native (installed) | native CUDA builds | **no official Windows support**. WSL2, Docker, or unofficial forks ([fazm](https://fazm.ai/t/vllm-windows-support-2026), [Docker Model Runner](https://www.docker.com/blog/docker-model-runner-vllm-windows)) |
| 6 GB fit | GGUF Q4 with automatic CPU offload | same, with finer control (`-ngl`, `--cache-type-k q8_0`) | FP16/AWQ/GPTQ. Preallocates `gpu_memory_utilization` of VRAM. Realistic only for ≤4B AWQ at ≤8k context. WSL memory and disk (~8–10 GB torch+vLLM on C:) hurt |
| Structured output | `format`: `"json"` or a **JSON schema** (converted to a grammar). Also OpenAI-compatible `response_format` ([docs](https://docs.ollama.com/capabilities/structured-outputs)). **Verified** | GBNF grammars; `json_schema` / `response_format` on the server | `guided_json` / structured outputs via xgrammar or guidance. Best schema coverage |
| Tool calling | yes (`tools`, model-dependent; Qwen 2.5/3/3.5 tagged "tools") | yes (`--jinja`) | yes (parsers per model) |
| Vision | yes (Qwen3.5, Qwen3-VL, Qwen2.5-VL) | yes (mmproj) | yes |
| Model swap | automatic load/unload and `keep_alive` | manual (one model per server, or router mode) | one model per process |
| Verdict | **default** | fallback if we need custom grammars or Ollama lags on a new architecture | optional backend later (batch eval on a bigger GPU) |

### Structured-output guidance (applies to all runtimes)

- Keep the IR JSON schema **flat and non-recursive**. Use discriminated unions (`anyOf` with a `const` `op` tag), enums for ops and units, and `additionalProperties:false`. Avoid `$ref` cycles, `patternProperties` and complex `format`s. Grammar converters support only a subset of JSON Schema.
- Generate in stages (parts → sketches → features → joints) with smaller schemas. That improves 4B-class accuracy and keeps the grammar small.
- Always re-validate with Pydantic. On failure, send the error back (repair loop, at most 2 retries).
- For Qwen3/3.5 "thinking" models, pass `think: false` for schema-constrained calls (or use a two-call pattern: think freely, then emit constrained JSON). The interaction between thinking and `format` was **not verified** on 0.40.11. Test on day 1 of M1.
- Include the schema text in the prompt as well (Ollama's own recommendation), and use `temperature: 0`.

## Memory plan (sequential, single GPU)

- Resident: `qwen3.5:4b` (~4.5 GB at 16k) plus `qwen3-embedding:0.6b` (~0.7 GB) ≈ 5.2 GB. That fits, but it is tight. If it OOMs, run embeddings on CPU (`num_gpu: 0`) or with `OLLAMA_MAX_LOADED_MODELS=1`.
- The 7B A/B model replaces the 4B model (Ollama swaps it; reload takes about 3–6 s from NVMe).
- Serialise GPU jobs (concurrency 1) in the job system. Set `OLLAMA_NUM_PARALLEL=1`, because parallel slots multiply the KV cache.
- Images: Qwen-VL vision tokens ≈ (W/28)·(H/28) at 28 px patches after merge, so 1024² ≈ 1.3k tokens. Downscale sketches to ≤1024 px on the long side.

Sources: [ollama.com/library/qwen3.5](https://ollama.com/library/qwen3.5/tags), [qwen3](https://ollama.com/library/qwen3/tags), [qwen3-vl](https://ollama.com/library/qwen3-vl/tags), [qwen2.5-coder](https://ollama.com/library/qwen2.5-coder/tags), [qwen2.5vl](https://ollama.com/library/qwen2.5vl/tags), [qwen3-embedding](https://ollama.com/library/qwen3-embedding/tags), [Qwen3.5-4B card](https://huggingface.co/Qwen/Qwen3.5-4B), [Qwen3.5 small models](https://artificialanalysis.ai/articles/qwen3-5-small-models).
