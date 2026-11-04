# CX-13: fine-tuning on company design habits (parity-m5-conventions agent)

Row CX-13 (`docs/reference/PARITY_CHECKLIST.md`). Everything except the GPU run is built; the row stays open until `training/wsl/cx13.sh` has run and the demo passes on the tuned model.

## Profile

`evals/parity/m5/house-style.md`, house style HS-1, invented for this row:

| id | Convention |
|---|---|
| wall | 2.5 mm walls and floor on enclosures, trays and housings |
| insert | unsized screw points are M3 heat-set inserts: Ø4.0 bore, 6 mm deep; Ø13 corner bosses on enclosures |
| fillet | 1 mm fillet on every vertical outside edge |
| edge | hole centres ≥ 2 × D from any outside edge (8 mm) |
| names | parameter names end in their unit: `_mm`, `_deg`, `_n` |

## Corpus (`scriber-conventions`)

`training/src/scriber_training/house.py` draws open-top enclosures (70 % with insert bosses) and plates (corner inserts or a pitched row) with the existing `Draft` machinery. Requests give sizes, counts and pitches only; never the spec-sheet style, which would list the parameter names. Convention values carry `rule` provenance citing `house-style.md#<id>`. Samples are generate plus repair (the existing mutator), all built and checked under the default rules; the 8-gram leak guard now includes `evals/cases/conventions.yaml`. The S0–S2 pipeline is unchanged: none of the S0, S1 or S2 samples shares an 8-gram with the new cases.

Dry run (`--specs 1000`, seed 13, default): 1000 of 1000 specs verified, 1,483 samples (1,000 generate, 483 repair), 742 enclosure / 741 plate, mean 6.0k characters, longest 9.7k. About 3 min with 8 kernel workers.

## Benchmark and demo

`evals/cases/conventions.yaml`: 20 held-out requests in their own wording (10 enclosures, 10 plates; 3 enclosures without screw points, rows of 2–6 holes). None states a convention (`test_benchmark_cases_never_state_the_house_style`).

Each case scores the conventions it lists, 0–100 (share followed):
- wall: four side walls of 2.5 ± 0.05 mm, from a mid-height section (as CX-8);
- insert: exactly the requested number of holes, all Ø4.0 ± 0.05;
- fillet: a fillet whose radius evaluates to 1 mm;
- edge: every vertical hole ≥ 2 × D from the part's outline;
- names: every parameter name ends in its unit.

A case with no design scores 0, and the geometric conventions need a built part.

`parity_m5_conventions.cx_13` runs the agent on every case with `rig.llm` (the candidate) and with the base model named by `SCRIBER_CX13_BASE` (default `qwen3.5:0.8b-q8_0`). It passes when the candidate's mean beats the base's by ≥ 10 points. Per-case scores land in `scores.json` beside the evidence. The offline test (`evals/tests/test_parity_m5_conventions.py`) scripts a house-style model and a plain one: 100 against 0 passes; plain against house, or the same model on both sides, fails.

## Run

1. WSL (`~/scriber-train`, pinned venv, llama.cpp b11898 with `llama-quantize`): `bash <repo>/training/wsl/cx13.sh`. It generates the corpus on Windows through interop if `data/training/cx13/train.jsonl` is missing. Then it trains QLoRA r16 on Qwen3.5-0.8B (4-bit base, batch 2 × 4, 4,096 tokens, 1 epoch, about 186 steps), merges with `merge.py`, converts to a bf16 GGUF and quantises to Q8_0, the base 0.8B's format.
2. Windows: `ollama create scriber-ir:0.8b-cx13 -f training/wsl/Modelfile.0.8b-cx13`.
3. Windows: `uv run scriber-parity CX-13 --model scriber-ir:0.8b-cx13`.

Expected GPU time, an estimate from S0 (bf16 LoRA on the 0.8B: 247 steps of similar-length samples in 47 min, 4.4 GB): about 35–50 min of training. QLoRA's 4-bit base may be slower per step than S0's bf16, which was not measured on the 0.8B. Merge, convert and quantise take a few minutes.

Before step 3, two one-line registrations are needed. This change leaves both files alone:
- `parity_m5_conventions` in `registry()` (`evals/src/scriber_evals/parity.py`);
- `scriber-ir:0.8b-cx13: {num_ctx: 8192, think: false, few_shot: false}` in `config.yaml`, so the tuned model is prompted the way it was trained.

## Open

- The adapter learns only the HS-1 families. It is a demonstration of the habit-learning path, not a replacement for the default model.
- A request that names a value should override the profile. The corpus never shows such a request, so the benchmark does not test it.

## Result (2026-10-29)

`training/wsl/cx13.sh`: 186 steps in 49 min, export 5 min, `scriber-ir:0.8b-cx13` (Q8_0, 834 MB). On the 20 held-out cases the adapter scores 60.3 against 2.5 for the base `qwen3.5:0.8b-q8_0` (`evals/results/parity-20261029-171950`), so CX-13 passes. It learned the house style for enclosures and plates only; it is a demonstration, not a default model.
