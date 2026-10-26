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

## Reference: Claude Sonnet 5.5 as the agent's model (comparison only)

Run 2026-10-26 on the user's Claude subscription, not part of the product path. Each attempt was a fresh Sonnet 5.5 subagent that saw only what the agent's model sees: the system rules, the five worked examples, the request, the IR JSON schema and, for repairs, the agent's own repair message quoting its previous answer. It never saw the case checks. Requirement extraction used one Sonnet subagent with the agent's extraction prompt. Answers were scored with our own validator, kernel, requirement checks, parameter and +5 % robustness checks, up to 4 attempts, as `partwright-evals` does. Differences from the Ollama path: no constrained decoding (answers were plain JSON) and Claude Code's own system prompt around the task. Harness, scorecard and final designs: `evals/results/sonnet-5-5-subagents-20261026/`.

| Set | Sonnet 5.5 | qwen3.5:4b (prompted) | tuned 0.8B S0b |
|---|---|---|---|
| M1 (10) | **10/10**, 35/35 checks, 8 on the first attempt | 4/10, 15/35 | 0/10, 3/35 |
| Challenge (2) | **2/2**, 29/29 checks (c01: all 16 named parameters, every robustness rebuild), both on the first attempt | 0/2 | 0/2 |

What it shows:

- The IR v2, compiler, kernel and checks can express and verify the challenge manifold; the remaining gap is entirely model capability.
- Two failures came from our requirement extraction, not the model: "plate thickness 4" extracted as an overall extent for an L-bracket (the bounding box of an L is legs x width, so it can never be 4), and a "wall 2" requirement on an open box, which the wall check can only measure through holes. Both cost the local models repairs too; they are agent bugs to fix.

## S1 and the stop rule

S1 data (`partwright-dataset --seed 1 --specs 2900 --paraphrase-model qwen3.5:4b`): 4898 verified samples, 2821 generate / 1429 repair / 648 requirement; 1110 local paraphrases (terse, chatty, engineer, messy) that passed the number and meaning checks, 345 vague requests, 760 document-grounded requests, open boxes added. Same recipe as S0b, 608 steps, 2 h 12 min, mean loss 0.027. Served as `partwright-ir:0.8b-s1`.

| Gate | tuned 0.8B S1 | tuned 0.8B S0b | qwen3.5:4b (prompted, after the key-order fix) |
|---|---|---|---|
| M1 (`m1-20261026-212853`, 4B: `m1-20261026-150432`) | 3/10, 10/35 checks, 6/10 built, median 16 s | 0/10, 3/35 | **4/10, 15/35**, median 68 s |
| Grounded, grounded mode (`grounded-20261026-213112`, 4B: `grounded-20261026-213513`) | 1/10, **24/45**, 8/10 built, 18/25 citations correct, median 11 s | not run | 1/10, 14/45, 5/10 built, 10/15 correct, median 98 s |
| Grounded, prompt mode | 2/10, **30/45**, 9/10 built | not run | 2/10, 12/45, 3/10 built |

Stop rule (`docs/FINE_TUNING_PLAN.md`): S1 had to beat the prompted 4B on M1 and on the grounded set. It does not beat it on M1 (3/10 and 10/35 against 4/10 and 15/35), so **the 0.8B route stops here**, as the rule says. On the grounded set it ties on fully passing cases, passes more checks, builds more parts and is about nine times faster; that is recorded, not a reason to bend the rule.

The 4B's grounded score fell from 3/10, 23/45 (`grounded-20261026-035401`) to 1/10, 14/45 since the key-order and request-override changes. That needs a look before the next 4B work: the request-override logic, the reordered worked examples, or run-to-run variance.

## The prompted 4B after the fixes (2026-10-26)

The grounded drop (3/10 to 1/10) was traced with an A/B on the three cases that regressed: current prompt 0/3, old example key order 1/3 (g02 passes, g01 now fails), project block without the new request-wins line 0/3. No single change explains it; the 4B's greedy answers flip with small prompt changes (recorded in KNOWN_ISSUES). The old example order cannot come back, since it teaches keys the grammar cannot emit.

After dropping requirements the checks cannot measure (bent-part stock thickness, walls on non-round parts):

| Gate | qwen3.5:4b before | qwen3.5:4b now |
|---|---|---|
| M1 (`m1-20261026-222758`) | 4/10, 15/35 | **5/10**, 16/35, median 68 s |
| Grounded, grounded mode (`grounded-20261026-223718`) | 1/10, 14/45 | 1/10, 14/45 (unchanged; no unmeasurable requirements there) |
| Grounded, prompt mode | 2/10, 12/45 | **4/10**, 20/45 |

## S1 on the 4B with QLoRA (started 2026-10-27)

bf16 LoRA on Qwen3.5-4B needs about 10 GB, so the run uses QLoRA (base weights 4-bit, Unsloth advises against it for Qwen3.5 on quality grounds; the gates decide). Probes, 20 steps, batch 1 x 8 accumulation: 4,096 tokens peaks at 5.17 GB and 52 s per step, 2,048 tokens at 4.57 GB and 36 s. The full run uses 4,096 so the long spec-sheet and repair samples stay in: 608 steps, about 9 hours, a checkpoint every 100 steps, adapter only (merging a 4B to bf16 needs more RAM than WSL has, so it is a separate step). Base weights: `Qwen/Qwen3.5-4B` from Hugging Face in WSL (`~/models/Qwen3.5-4B`, 9.3 GB). Same gates and stop rule as S1.
