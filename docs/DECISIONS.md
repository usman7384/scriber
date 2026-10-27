# Decisions

One entry per decision: context, decision, consequence. Newest last.

## D-001 Project name: Partwright (2026-10-25)
The brief asked for an original name instead of the working title. "Partwright" (a maker of parts) is short and descriptive. Not trademark-checked; rename before any public release if a conflict turns up.

## D-002 Models sized to a 6 GB GPU (2026-10-25, revised same day)
The machine has an RTX 3060 Laptop with 6 GB VRAM and 16 GB RAM (`docs/HARDWARE.md`); 32B/14B-class models cannot run. Default IR and vision model is `qwen3.5:4b` (multimodal, Apache-2.0, cheap KV cache, so no model swap between IR and vision). `qwen2.5-coder:7b-instruct-q4_K_M` (already on disk) is the A/B baseline; the M1 eval decides the default and the loser stays configurable. Embeddings `qwen3-embedding:0.6b`; CI `qwen3.5:0.8b-q8_0` plus a fake LLM for unit tests. Avoid Qwen2.5-Coder-3B and Qwen2.5-VL-3B (non-commercial licence).

## D-003 Ollama as the default runtime (2026-10-25)
Ollama is installed, serves the 7B fully on GPU, and supports JSON-schema `format` on Windows (verified). vLLM needs WSL and has no headroom at 6 GB; an OpenAI-compatible adapter covers vLLM/llama.cpp server as an option behind the same `LLM` interface.

## D-004 Research via in-session sub-agents (2026-10-25)
M0 research (reference and technical) runs as parallel background sub-agents whose results feed the parity checklist and plan in this session. Build agents (M1+) work on separate git branches/worktrees per `docs/PLAN.md`.

## D-005 Licence: Apache-2.0 (2026-10-25)
Dependency check in `docs/research/SUMMARY.md`. OCCT and planegcs (LGPL) are used only as separately installed wheels with a NOTICE entry. Excluded: PyMuPDF (AGPL), marker, python-solvespace, BOLTS, FreeCAD Fasteners WB, CADAM code, Neo4j server. Non-commercial datasets (Fusion 360 Gallery, Text2CAD, CAD-Recode) are eval-only; published weights train on our procedural corpus and permissive data.

## D-006 Python 3.12, build123d only (2026-10-25)
`planegcs` (sketch constraint solver) ships cp312+ wheels only. build123d 0.13.0 on OCP 8.0.1 is the single CAD library; CadQuery 2.8 pins OCP 7.9 and breaks when co-installed (verified), so CadQuery is not a dependency. The kernel sits behind `services/geometry`'s interface, so a CadQuery backend could still be added in its own environment.

## D-007 Feature tree: IR is the source of truth; FreeCAD `.FCStd` as the native history format (2026-10-25)
STEP carries no feature history. Every model ships as IR JSON + generated build123d script + STEP/STL/GLB, and the IR is replayed into a FreeCAD `.FCStd` (PartDesign bodies, constrained sketches, named features, assembly joints) by an optional FreeCAD 1.1 subprocess. This is the open counterpart of the reference product's native Onshape output. Onshape (proprietary SaaS) is an optional adapter tested only against a recorded mock, never on the default path.

## D-008 Local-first stack without Redis (2026-10-25)
Jobs: in-process asyncio dispatcher with a SQLite job table and warm subprocess CAD workers with timeouts; one GPU job at a time. Celery has no Windows support, RQ needs fork, arq is maintenance-only. Progress streams over SSE. One SQLite file per project holds documents, chunks, FTS5, `sqlite-vec` vectors and the property graph (networkx in memory for traversal). Kùzu is archived. Postgres-readiness means SQLAlchemy Core with no SQLite-only SQL outside the vector/FTS module.

## D-009 Business and proprietary rows are scoped, not dropped (2026-10-25)
Checklist rows that are business features (quotas, community), proprietary formats (CATIA/NX/SolidWorks/Creo, Onshape) or the reference's own stated vision (supplier catalogs, differentiable workflow) are built in the smallest form that passes their acceptance test (e.g. STEP AP242 for proprietary CAD, mock-tested Onshape adapter) and any gap is listed in `docs/PARITY_REPORT.md`.

## D-010 M1 agent loop shape (2026-10-25)
One schema-constrained call emits the whole `Design`; staged emission (params → sketches → features) is added only if the M1 eval shows the single call failing on structure. A separate small call extracts checkable requirements (extent, hole count/diameter, hole spacing, wall) from the request; the loop checks the built model against them and against B-rep validity, and every failure is fed back as a repair message. Refinement answers either parameter updates or a full new design, so a pure parameter change cannot drift the rest of the model.

## D-011 Holes are recognised from the B-rep, not trusted from the IR (2026-10-25)
Spec checks read holes from the built solid: concave cylindrical faces grouped by axis and radius whose angular span adds up to 360°. This catches holes that miss the part, are blind by accident, or were never cut, and does not count slot ends or internal fillets.

## D-012 Default model confirmed: qwen3.5:4b (2026-10-25)
M1 eval: 4B fully passes 4/10 cases vs 3/10 for the 7B coder, with 21 vs 27 repairs and 145 s vs 172 s median; both pass 22/35 checks. The 4B stays default; the 7B stays configurable.

## D-013 No planning step; keep standards data, normalisation and strict hole checks (2026-10-25)
Ablation on the M1 set with `qwen3.5:4b`: a free-text planning call before IR emission scored 1/10 cases fully correct (8/35 checks); the same build without it scored 6/10 (24/35 checks, median 84 s), up from the M1 baseline of 4/10 (22/35, 145 s). The plan step was deleted. Kept: EN 1092-1 / NEMA / extrusion reference data, linking literals to unused parameters (unused ones stay errors), unused-sketch errors, holes that miss or break the edge failing with the feature named. Results in `evals/results/m1-20261025-223518` (with plan) and `m1-20261025-225624-noplan`.

## D-014 Grounding: facts become checks, citations by fact id (2026-10-25)
Retrieved facts are listed in the prompt with their ids; the model cites a fact by putting its id in a parameter's provenance, and the agent swaps in the fact's document provenance (ref + quote). Checkable facts (hole callouts, toleranced bores, size chains) become requirement checks, so the spec is enforced by geometry, not trusted from the model. Project rules reach the geometry service per process. The agent depends on `partwright_context` only for its data types; retrieval and recording happen at the edge (CLI, later the API).

## D-015 Unused parameters are dropped; repairs are fresh prompts (2026-10-25)
Failing on unused parameters made the 4B churn (it adds parameters for rule limits); requirement checks already catch a forgotten dimension, so unused parameters are removed before validation. Repairs re-send the original prompt plus a user message quoting the previous design and its problems, because the 4B repeated its last assistant turn verbatim in a growing chat even at temperature 0.5 (sampling itself was verified to vary). An exact repeat raises the temperature to 0.9.

## D-016 Rules have no scope yet (2026-10-25)
"Hole-to-edge ≥ k x D" applies to every hole, including large bores where it cannot hold (a centred Ø40 bore on an 80 mm plate). The M2 demo spec was changed to a Ø20 bore. A `scope` on `Rule` (e.g. fastener holes up to a diameter) is an IR change planned with the M3 API work.

## D-017 IR v2 P0 (2026-10-26)
Implemented as proposed in `docs/IR_V2.md`: plane references (base, datum, or a face of an earlier feature), selectors, path sketches, extrude extents with intersect and taper, revolve axis offset, semantic holes and patterns, part process. Face planes keep the base-plane coordinates of their axis and an outward offset, so the model learns one coordinate convention; cuts on a face go into the material and adds go outward automatically. Feature tools are kept by id so faces can be referenced and patterns can replay them. Regions are resolved by geometric match with the tool body. v1 designs upgrade on load (the upgrade is idempotent and always applied), and every v1 fixture rebuilds unchanged.

## D-018 Fasteners as designations (2026-10-26)
`fastener` takes `M<d>` or `M<d>x<pitch>` for M2–M30. Clearance follows ISO 273 by fit, tap drill is nominal minus pitch (ISO 261 coarse pitch by default), counterbore seats follow DIN 974-1 style head-plus-clearance, countersinks follow the ISO 10642 head diameter (2.24 d). The model wrote fine-pitch hydraulic port threads (M18x1.5, M30x1.5) as soon as v2 allowed them; a closed `M\d+` pattern rejected realistic designs, so the field is validated by parsing rather than by schema pattern.

## D-019 Single-call emission stays; staged emission deleted (2026-10-26)
A/B on IR v2 with qwen3.5:4b, same code: drafting parameters first and then the design scored 2/10 fully correct and 9/35 checks on the M1 set against 4/10 and 16/35 for one call, and was slower on the challenge set. As with the planning step (D-013), a constrained first answer that the second must follow passes its mistakes along. The switch and its prompt were removed.

## D-020 IR v2 kept although the M1 gate regressed (2026-10-26)
v2 is required for completeness (faces, datums, semantic holes) and improves the grounded set (3/10, 23/45 checks vs 2/10, 15/45), but the M1 set fell from 21/35 to 16/35 checks and generation is about twice as slow. v1 cannot express the challenge parts at all, so reverting is not an option; recovering the M1 score on v2 is the next task, before further IR growth. Results: `docs/agents/ir-v2.md`.


## D-021 Fine-tuning stays local (2026-10-26)
Training runs on the laptop only (RTX 3060 6 GB, WSL2, Unsloth bf16 LoRA), so the model we tune is Qwen3.5-0.8B; the 4B needs about 10 GB. Data comes only from our generators, kernel and local models. Ollama on Windows cannot import Qwen3.5 safetensors (it needs its MLX runtime), so the merged model is converted with llama.cpp's `convert_hf_to_gguf.py` (release b11898, pinned) to q8_0 and imported as a GGUF with the base model's renderer, parser and sampling parameters. Plan: `docs/FINE_TUNING_PLAN.md`; runs: `docs/agents/training.md`.

## D-022 Answers are written required-keys-first (2026-10-26)
Ollama's schema grammar emits all required keys of an object before any optional one. Our worked examples and the first training targets wrote some optional keys early (a sketch's `plane` before `entities`, a part's `material` and `process` before `sketches`), and under constrained decoding the model can never produce them there: profiles and turned parts silently fell back to the XY plane. A tuned 0.8B scored 24 of 27 held-out cases on the first try without the grammar and 16/40 with it. `answer_json` now writes every design we show or train on in grammar order; all earlier eval numbers with the examples were measured under this bug.

## D-023 The request overrides conflicting project facts (2026-10-26)
A request in a project whose documents say otherwise ("100 x 60 x 5" against a spec sheet's 120 x 80 x 6) produced both sets of numbers as hard checks, so no answer could pass. When the request states an extent or a counted hole group that differs from a fact of the same kind, the fact's check is dropped, the fact is left out of the prompt, and the requirements step names what was overridden. Facts the request does not contradict (a bore it does not mention) still apply. Design rules are unchanged: a request that breaks a rule (holes 8 mm from the edge where 1.5 x D needs 8.25) still fails the rule.

## D-024 The local 0.8B fine-tuning route stops after S1 (2026-10-26)
The stop rule set before S1 required the tuned model to beat the prompted qwen3.5:4b on M1 and on the grounded set. S1 scored 3/10 and 10/35 checks on M1 against the 4B's 4/10 and 15/35; on the grounded set it tied on fully passing cases (1/10) with more checks (24/45 against 14/45) and was about nine times faster. The route stops as the rule says. The pipeline stays (generators, verification, local paraphrasing, training and GGUF export are reusable), and the reference run (Sonnet 5.5: 10/10 on M1, 2/2 on the challenge set) shows the IR and checks are sufficient, so the gap is model capability. Next work goes to the prompted local model and to the agent bugs the runs exposed.

## D-025 The QLoRA-tuned 4B stays a comparison model (2026-10-27)
S1 data on Qwen3.5-4B with QLoRA (local, 8 h, exported as Q4_K_M like the base) beat the prompted qwen3.5:4b on the grounded set (grounded mode 4/10 and 25/45 against 1/10 and 14/45; prompt mode 5/10 and 35/45 against 4/10 and 20/45) and was about twice as fast, but scored 4/10 and 13/35 on M1 against 5/10 and 16/35. The stop rule needs both gates, so the default stays the prompted 4B and `partwright-ir:4b-s1` is kept in `config.yaml` for comparison. Its M1 failures fit requests to our generator families (hole sizes snapped to clearance tables, patterns read as edge margins, quotes not in the prompt), so the next data work is breadth outside those families, not more of the same.
