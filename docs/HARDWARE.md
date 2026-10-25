# Hardware

Measured 2026-10-25 on the development machine. Model choices are finalised in `docs/research/SUMMARY.md` and `config.yaml`.

| Item | Value |
|---|---|
| OS | Windows 11 Home 10.0.26200; WSL2 Ubuntu (Python 3.12.3, GPU visible) |
| CPU | AMD Ryzen 9 5900HS, 8 cores / 16 threads |
| RAM | 16 GB |
| GPU | NVIDIA RTX 3060 Laptop, 6 GB VRAM, compute 8.6, driver 592.00 (plus AMD iGPU) |
| Disk free | D: ~14 GB, C: ~14 GB (fell from ~23 GB during M0, other processes); WSL vhdx, Ollama models, HF cache (55 GB) and uv cache (~9 GB) are on C: |
| Python | 3.11.9 (Windows), uv 0.9.13 |
| Node | 22.22.3, npm 10.9.8 |
| Other | git 2.52, Docker Desktop 29.9.2 |
| Model runtime | Ollama 0.40.11 (Windows, llama.cpp runner, 100% GPU offload for 7B Q4) |

## Models already present

| Where | Model | Size |
|---|---|---|
| Ollama | `qwen2.5-coder:7b-instruct-q4_K_M` | 4.7 GB |
| Ollama | `arh-qwen2.5-coder-7b-8k:latest` (same weights, 8k context; user's own) | 4.7 GB |
| HF cache | Qwen2.5-Coder-0.5B / 1.5B (base), Qwen2.5-0.5B/1.5B-Instruct, Qwen3-0.6B, all-MiniLM-L6-v2 | — |

## Consequences

- 32B- and 14B-class models do not fit in 6 GB VRAM. The reasoning/IR model is 7B–8B class at Q4 with 8k–16k context.
- Vision and reasoning models cannot be resident together; vision loads on demand (Ollama swaps models).
- Embeddings are small enough to run alongside or on CPU.
- Fine-tuning runs on 0.5B–1.5B models (LoRA) for the toy pipeline; 7B QLoRA is at the edge of 6 GB.
- Disk is the tightest resource: every model pull and dependency must be justified.
