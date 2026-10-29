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

Run: 608 steps in 7 h 58 min, mean loss 0.018, peak 6.15 GB reserved. The adapter was merged afterwards with Unsloth, shard by shard, which fits in WSL's 7 GB. It was then converted to a bf16 GGUF and quantised with llama.cpp's `llama-quantize` (b11898, CPU build) to Q4_K_M, the base 4B's format, giving 2.8 GB. Served as `partwright-ir:4b-s1` (`training/wsl/Modelfile.4b`, the base 4B's renderer, parser and sampling parameters).

| Gate | tuned 4B S1 (QLoRA) | qwen3.5:4b (prompted, `m1-20261026-222758`, `grounded-20261026-223718`) |
|---|---|---|
| M1 (`m1-20261027-084111`) | 4/10, 13/35 checks, 6/10 built, median 35 s | **5/10, 16/35**, median 68 s |
| Grounded, grounded mode (`grounded-20261027-084807`) | **4/10, 25/45**, 8/10 built, 26/35 citations correct, median 25 s | 1/10, 14/45 |
| Grounded, prompt mode | **5/10, 35/45**, 9/10 built, median 21 s | 4/10, 20/45 |

Stop rule: the tuned 4B beats the prompted 4B clearly on the grounded set, but not on M1. It is one case and three checks behind on a 10-case set sampled once, but the rule asks for both gates, so **S1 on the 4B does not replace the default**.

The M1 failures are the 0.8B's failure mode again, weaker: the model fits requests to our generator families.
- `nema17-plate` reads "31 mm square" as an edge margin, so the hole spacing is negative and the part never builds.
- `dp2-flanged-adapter` becomes a revolved part with M5 holes instead of the stated 8.5 mm ones, and quotes text that is not in the prompt.
- `dp3-dn50-flange` uses 17.5 mm (M16 clearance) for the stated 18 mm holes.

The low final loss (0.018) fits that reading: the data is learnable, but too narrow.

## Agent fixes before S2 (2026-10-27, D-026)

Re-sampling repeated answers, and treating prompt quotes that are not in the request as problems. The prompted 4B, rerun with both:

| Gate | qwen3.5:4b before (`m1-20261026-222758`, `grounded-20261026-223718`) | qwen3.5:4b with the fixes (`m1-20261027-121813`, `grounded-20261027-122553`) |
|---|---|---|
| M1 | 5/10, 16/35, median 68 s | 4/10, 15/35, median 52 s |
| Grounded, grounded mode | 1/10, 14/45 | 3/10, 25/45, 21/27 citations correct |
| Grounded, prompt mode | 4/10, 20/45 | 4/10, 21/45 |

Neither fix changed these numbers. The base 4B gave no repeated answers in either run, and the quote check fired only on g03 (attempts 2-4: a remark such as "Corrected coordinate to keep hole within bounds" written as a quote), which fails either way.
- The M1 loss is dp7: its first answer differed from the earlier run at temperature 0, and with no measurable screw-hole requirement extracted, a hole-less third attempt was accepted.
- The grounded gains (g02 and g04 pass in grounded mode) come from different first answers, not from repairs.
- Both swings come from different first answers between days, not from the fixes (KNOWN_ISSUES).

The fixes target the tuned models: in the stored S1-4B attempts, 4 of the 5 never-built M1 cases repeated one answer on every repair, and 3 of its answers invented quotes. The baseline S2 has to beat is noisy, which argues for repeated gate runs (open question in `docs/FINE_TUNING_PLAN.md`).

The tuned 4B with the same fixes (`m1-20261027-130825`, `grounded-20261027-131956`), same code as the prompted rerun:

| Gate | tuned 4B before the fixes | tuned 4B with the fixes | prompted 4B with the fixes |
|---|---|---|---|
| M1 | 4/10, 13/35, 6/10 built | **5/10, 16/35**, 7/10 built, median 68 s | 4/10, 15/35, 5/10 built |
| Grounded, grounded mode | 4/10, 25/45, 8/10 built | **4/10, 33/45, 10/10 built**, 34/45 citations correct | 3/10, 25/45, 7/10 built |
| Grounded, prompt mode | 5/10, 35/45 | 5/10, 30/45, 8/10 built | 4/10, 21/45 |

Where the fixes fired:
- **Repeats:** none remain on M1. Before the fixes, dp21, dp6, in2 and nema17 each repeated one answer through all four attempts; now every attempt is a different answer, and dp6 (the 2020 T-plate) passes after one repair. In grounded, one repeat survived (g05, 3 distinct answers in 4 attempts).
- **Quotes:**
  - dp3 dropped its quoted standard values ("165 mm", "125 mm") over three repairs.
  - dp2 kept inventing quotes.
  - nema17's one invented quote was flagged on its first attempt.
  - No grounded-mode answer misquoted.

On the same code, the tuned 4B is ahead on both gates: M1 by one case and one check, grounded by one case and eight checks, with every part built. The M1 margin is one case, so the three-run comparison below was run before any change of default. The remaining M1 failures are the template-fitting ones S2 targets: 17.5 mm for 18 mm holes (dp3), a revolved adapter without its bolt pattern (dp2), and margin-placed grids (nema17, in2).

### Three runs per model on the same code (2026-10-27)

Each model was run on M1 and the grounded set three times, back to back, with the fixes in place.

| Gate | tuned 4B (`partwright-ir:4b-s1`) | prompted `qwen3.5:4b` |
|---|---|---|
| M1, fully passing | **5, 5, 5** of 10 | 4, 4, 4 |
| M1, checks | **16, 15, 16** of 35 | 15, 15, 15 |
| Grounded mode, fully passing | **4, 3, 4** of 10 | 3, 3, 3 |
| Grounded mode, checks | **33, 27, 33** of 45; 10/10 built every run | 25, 25, 25; 7/10 built |
| Prompt mode, fully passing | **5, 4, 5** of 10 | 4, 4, 4 |
| Prompt mode, checks | **30, 34, 30** of 45 | 21, 21, 21 |
| M1 median s | 68, 48, 79 | 52, 67, 69 |

Runs: tuned `m1-20261027-130825`, `m1-20261027-135502`, `m1-20261027-150842`, `grounded-20261027-131956`, `grounded-20261027-140409`, `grounded-20261027-152238`; prompted `m1-20261027-121813`, `m1-20261027-142548`, `m1-20261027-154654`, `grounded-20261027-122553`, `grounded-20261027-143606`, `grounded-20261027-155749`.

The tuned 4B is ahead on every gate in every run, so the S1 stop rule is now met on the same code. The repeats are near-identical (KNOWN_ISSUES), so they show the lead is not a one-off, not that it is statistically significant.

The M1 passes differ by case:
- the tuned model passes dp6 (2020 T-plate) and dp7 (angled bracket);
- only the prompted model passes nema17, which the tuned model reads as an edge margin.

`partwright-ir:4b-s1` became the default on this basis (D-027).

## Rebuilding the default model on a fresh clone

`partwright-ir:4b-s1` is not published, so it is built from the repo. It takes about 9 h on an RTX 3060 6 GB, needs about 20 GB free on the WSL disk while merging, and ends as a 2.8 GB GGUF. Same stack as the S0 run (`training/wsl/requirements.txt`), plus llama.cpp b11898 built with `cmake -B build -DGGML_CUDA=OFF && cmake --build build --target llama-quantize`.

1. Data (Windows, Ollama running with `qwen3.5:4b`): `uv run partwright-dataset --seed 1 --specs 2900 --paraphrase-model qwen3.5:4b --out data/training/s1`. Paraphrases come from the local 4B, so the samples are close to ours, not byte-identical.
2. Base weights in WSL: `Qwen/Qwen3.5-4B` from Hugging Face into `~/models/Qwen3.5-4B` (9.3 GB).
3. Train (WSL, `~/partwright-train`):
   `python train.py --data /mnt/d/Projects/bye-kyrall/data/training/s1/train.jsonl --model ~/models/Qwen3.5-4B --out runs/s1-4b --load-4bit --max-seq 4096 --batch 1 --accum 8 --save-steps 100 --no-merge`
4. Merge: `python merge.py --lora runs/s1-4b/lora --out runs/s1-4b/merged` (`training/wsl/merge.py`).
5. Convert and quantise:
   `python llama.cpp/convert_hf_to_gguf.py runs/s1-4b/merged --outtype bf16 --outfile runs/s1-4b/s1-4b-bf16.gguf`
   `llama.cpp/build/bin/llama-quantize runs/s1-4b/s1-4b-bf16.gguf /mnt/d/Projects/bye-kyrall/data/training/s1-4b/run/partwright-ir-4b-s1-q4_k_m.gguf Q4_K_M`
6. Import (Windows, from `training/wsl`): `ollama create partwright-ir:4b-s1 -f Modelfile.4b`.

Check the result with `uv run partwright-evals evals/cases/m1.yaml --models partwright-ir:4b-s1` (5/10 expected). The LoRA adapter of the run recorded here (85 MB) is kept at `~/partwright-train/runs/s1-4b/lora` on the training laptop; with it, steps 1 and 3 can be skipped.

## S2 data (built 2026-10-27, D-029)

What changed in `training/` (S2 items in `docs/FINE_TUNING_PLAN.md`):

| Item | Where | Done |
|---|---|---|
| 1. Holes by what the request says | `holes.py` (`bore`) in plates, blocks, brackets, profiles | about 60 % of holes by stated diameter, the rest by M-size or both |
| 2. Placement by what the request says | `holes.py` (`corner_grid`), plate hole grids, PCD wording | margin, centre spacing, square, rows x columns |
| 3. New outlines and families | `families/profiles.py` | flat L, T, U, gusset and slotted plates from a corner; rounded inside corners as paths |
| 4. Standard parts | `families/standards.py` | EN 1092-1 flanges, NEMA 8/11/14 plates, 30 and 40 series extrusion plates; eval sizes left out |
| 5. Names decoupled | `names.py` | parameters renamed to synonyms in about half the specs |
| 6. Real repairs | `collect.py` (`partwright-collect`), `mutate.py` | first answers of a real model, plus fillet-too-large and overlapping-hole mutations |
| 7. Honest provenance | `dataset.py` | samples whose target quotes words not in the request are dropped |
| 8. Edits that keep values | `context.py` (`edited`) | previous design in context, one value changed, the rest carried over |

The prompts also carry the agent's reference lines (EN 1092-1, NEMA, extrusions), as inference does; S1 prompts did not. Fix found on the way: the agent's extrusion lookup missed 30-series profiles such as 3030.

Draft card (`partwright-dataset --seed 2 --specs 700`, no paraphrasing, `data/training/s2-draft`): 684 of 700 specs verified, 1,153 samples (679 generate, 307 repair, 167 requirement), 54 edits. The families are balanced at about 160 samples each.

| Coverage | S1 | S2 draft |
|---|---|---|
| Holes by stated diameter | 22 % | 59 % |
| Distinct titles | 50 | 85 |
| Distinct parameter names | 57 | 126 |
| Slot / path entities | 0 / 0 | 30 / 12 |
| Through-all cuts, mirror patterns | 0 / 0 | 3 / 9 |
| Eval sizes in prompts | — | 0 |

Through-all cuts stay rare (about 0.4 %), below the plan's 2 %.

The 8-gram leak guard dropped most L-plates at first, because one phrase ("mm apart on the centre line of the") matched dev case d07. The generators were reworded until leak drops fell to a handful of number-specific matches. For dev case d19, the dev wording was changed instead, because it repeated a long-standing generator phrase.

Dev-set baseline, default `partwright-ir:4b-s1` (`dev-20261027-164441`): 7/20 cases, 43/95 checks. Its misses are the S2 targets: 11 mm holes made 12.2, 5 mm made 7, 18 mm made 17.5, and the wrong slot pitch.

On-policy collection (200 specs each, temperature 0): `qwen3.5:4b` failed its first answer on 164, `partwright-ir:4b-s1` on 90.

Full S2 set (`partwright-dataset --seed 2 --specs 2900 --paraphrase-model qwen3.5:4b --onpolicy ...`, `data/training/s2`): 2,845 of 2,900 specs verified, 5,034 samples (2,834 generate, 1,534 repair, 666 requirement); S1 had 4,898. Repairs include 163 and 90 on-policy ones. 173 edits, 1,432 paraphrased or vague prompts, 0 eval sizes. Holes by stated diameter 2,138 against 1,475 by fastener; through-all cuts 11. The first attempt ran out of memory beside another process; it was rerun with `--workers 4` and `OPENBLAS_NUM_THREADS=1`, which does not change the data.

Next:
1. One night of QLoRA training on the 4B, then export.
2. Gates: dev for the checkpoint; M1 and grounded against the default in the same session (D-028).
