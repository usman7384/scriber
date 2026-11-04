# Scriber — rules for every agent and session

Scriber is an open-source AI design agent for mechanical CAD: text, specs, sketches, photos, meshes and past designs in; parametric, editable B-rep parts and assemblies out. Local open-weight Qwen models, open geometry (OCCT via build123d). Offline by default.

## Product constraints

- Capability parity with the reference product documented in `docs/reference/`, never asset copying. Do not use the reference product's name in code, repo name, UI or marketing text; it may appear only in `docs/reference/`, `docs/research/`, `docs/COMPARISON.md` and `docs/PARITY_*.md` as a cited reference.
- Do not copy their UI design, logo, copy, screenshots or videos. Same functions, our own implementation and look.
- Public sources only. No logins, no scraping behind auth, no probing their systems. Summarise in our own words with links.
- Open source throughout. No proprietary kernels or SaaS in the default path. Pin versions.
- Correctness over flash: a watertight, parametric, spec-matching part beats a pretty mesh.
- The model never emits raw geometry. It emits the typed IR (`services/ir`), compiled deterministically to build123d. Every parameter has a name, value, unit, bounds and provenance.
- Verification is part of generation: compile, validity, dimensional/spec checks, rule checks, DFM, vision critique, then repair.
- Write it down: `docs/DECISIONS.md`, `docs/KNOWN_ISSUES.md`, `docs/PARITY_REPORT.md`. A parity row is done only with a passing acceptance test and a recorded demo. Never silently stub or drop a row.

## Code style (non-negotiable)

- Clean and minimal. Smallest implementation that passes the tests. No speculative abstractions, plugin systems, unrequested config knobs, dead code, or wrappers around a library called once.
- No long comments. Names and structure explain the code. A comment only for a non-obvious why (workaround, geometric gotcha, spec reference), one line. No block comments, banners, or docstrings that restate the signature. Prose goes in `docs/`.
- Small files, small functions, flat modules. Prefer deleting over adding.
- Type hints everywhere in Python; strict TypeScript. ruff + mypy + eslint + prettier enforced in CI.
- Single responsibility per module and function. Clear service boundaries (geometry, ir, agent, context, api, web) with explicit typed interfaces; no cross-imports of another service's internals.
- Dependency inversion at the model and kernel boundaries: Qwen/Ollama/vLLM and build123d sit behind small interfaces.
- Pure functions where possible; side effects at the edges. No global state.
- Fail fast with explicit errors. No silent `except: pass`.
- DRY, but three similar lines beat a premature abstraction. YAGNI.
- Immutable data across boundaries (pydantic frozen models / frozen dataclasses).

## Tests and workflow

- Unit tests for pure logic, integration tests at service boundaries, one end-to-end test per parity row.
- Deterministic tests: seeded sampling, fixtures, no network. Integration tests use a small Qwen so CI stays fast.
- Every merge is small, reviewed against this file, passes CI, and has a one-paragraph description.
- Conventional commits. Semantic versioning once past M3.
- Each sub-agent writes `docs/agents/<name>.md` and states which checklist rows it closes.
