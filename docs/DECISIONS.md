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
