# Fine-tuning (training agent)

Plan: `docs/FINE_TUNING_PLAN.md`. Local only (decided 2026-10-26): every stage runs on this laptop (RTX 3060 Laptop, 6 GB; 16 GB RAM; WSL2 Ubuntu 24.04).
Closes: FT-1 (fine-tune pipeline, toy run) once the S0 gate below is recorded.

## S0 data (`partwright-dataset`, seed 0)

| | |
|---|---|
| Specs drawn | 1150 (plate, block, turned, bracket in rotation) |
| Verified (built, valid, every check passes) | 1127; 23 rejected by the kernel (chamfer or fillet too large) |
| Samples | 1977: 1127 generate, 572 repair, 278 requirement extraction |
| Prompt styles | one line, bullets, numbered requirements, spec sheet with required parameter names (about a quarter each) |
| Repair mutations | word in a numeric field 154, port outside its face 79, renamed parameter 71, wrong value 57, pattern before its source 40, dropped plane 38, dropped feature 36, no hole size 33, truncated answer 26, bad face name 21, revolved boss 17 |
| Held out | 40 cases in `evals/cases/synthetic.yaml`, generator seeds disjoint from training |
| Leakage guard | samples sharing an 8-word sequence with the M1, grounded or challenge prompts are dropped (none were) |
| Licence | all generated here; no third-party data |

Regenerate with `uv run partwright-dataset` (about 45 s with 8 kernel workers). Data lands in `data/training/s0/` (git-ignored) with `card.json`.

Training prompts are the inference prompts without the five worked examples (`few_shot: false` in `config.yaml`): the system rules, the request, and for repairs the same repair message the agent sends.

## S0 run

| | |
|---|---|
| Base | Qwen/Qwen3.5-0.8B (Apache-2.0), bf16, text layers only |
| Method | LoRA r16, alpha 16, all attention and MLP projections (6.4M trainable of 859M), loss on assistant turns only |
| Schedule | 1 epoch, 247 steps, batch 2 x 4 accumulation, lr 2e-4 cosine, max 4,096 tokens (longest sample 3,728) |
| Hardware use | 4.4 GB VRAM peak, 47 min, about 1,100 tokens/s (fallback kernels, see the S1 plan) |
| Loss | 0.43 at step 10, about 0.002 from mid-epoch, mean 0.032 |
| Stack | `training/wsl/requirements.txt` (Unsloth 2026.10.8, torch 2.14.1+cu130, transformers 5.17.0, TRL 1.15.0, PEFT 0.21.2), WSL2 Ubuntu 24.04 |

Reproduce (WSL, `~/partwright-train` with the pinned venv):

```
python train.py --data /mnt/d/Projects/bye-kyrall/data/training/s0/train.jsonl --model /mnt/d/Projects/bye-kyrall/data/models/Qwen3.5-0.8B --out runs/s0
python llama.cpp/convert_hf_to_gguf.py runs/s0/merged --outtype q8_0 --outfile /mnt/d/Projects/bye-kyrall/data/training/s0/run/partwright-ir-0.8b-s0-q8_0.gguf
```

llama.cpp is pinned to release b11898 (commit 8b28c2394324). Then on Windows: `ollama create partwright-ir:0.8b-s0b -f training/wsl/Modelfile` (833 MB). Ollama cannot import Qwen3.5 safetensors on Windows (its MLX runtime is missing), so the GGUF step is required.

## S0b (after the answer-order fix, D-022) and the gates

S0 was trained on answers whose key order the decoding grammar cannot produce; it is superseded. S0b uses the same recipe on regenerated data: 1972 samples, 59% with a project block (default rules, sometimes contradicting document facts, sometimes a prior design), every design verified under the default rules, plus an edge-distance repair mutation. 56 min, mean loss 0.034. Served as `partwright-ir:0.8b-s0b` (`training/wsl/Modelfile`).

All runs go through the full agent (requirements, constrained decoding, up to 3 repairs) via Ollama, 2026-10-26.

| Gate | Tuned S0b | Base 0.8B with examples | qwen3.5:4b with examples |
|---|---|---|---|
| Synthetic held-out (40, `synthetic-20261026-141104`) | **39/40**, 322/323 checks, median 6.9 s | 4/40, 39/323, 71.6 s | not run |
| M1 (10 real prompts, `m1-20261026-150432`) | 0/10, 3/35 checks, 19 s | 1/10, 6/35, 39 s | **4/10**, 15/35, 68 s |
| Challenge (2, `challenge-20261026-152752`) | 0/2, nothing built, 38–81 s | — | 0/2, nothing built, 220–379 s |

Reading:

- The S0 gate passes: in distribution, the tuned 0.8B goes from 4/40 to 39/40 and is ten times faster.
- It does not transfer. On M1 the tuned model is worse than its own base. Its answers are well formed but semantically wrong: it reads a hole diameter as an edge margin, draws an L-bracket as a solid rectangle without its thickness, and takes "mounting bracket ... 80x60 plate" to be an L profile, because in our data "bracket" always means one. It has learned our templates' wording, not the task.
- The 4B's M1 score is unchanged at 4/10 after the order fix, but its median time halved (133 s to 68 s): fewer repairs are spent on keys the grammar cannot emit.
