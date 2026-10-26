# Plan

Inputs: `docs/reference/PARITY_CHECKLIST.md` (138 rows), `docs/research/SUMMARY.md`, `docs/DECISIONS.md`, `AGENTS.md`.

## Repository layout

```
services/ir/        typed IR, JSON schema, compiler → build123d source, params, diff
services/geometry/  sandboxed execution, export, validity, DFM, measure, thumbnails, mesh→IR, FCStd replay
services/context/   ingestion, extraction (facts, rules), project DB (chunks, FTS5, vectors, graph), retrieval
services/agent/     LLM interface + adapters, generate/refine/edit/critique loop, vision path
apps/api/           FastAPI, jobs, projects/files/models/versions, REST + SSE, tokens, webhooks
apps/web/           Vite + React + TS + react-three-fiber
apps/cli/           `partwright generate | refine | params`; reads config.yaml
training/           procedural dataset generators, LoRA pipeline, GGUF export
evals/              benchmark specs + fixtures, harness, scorecard, parity demo suite
config.yaml         models, runtime, paths, limits
```

One uv workspace (Python 3.12); each service is its own package with its own `pyproject.toml` and tests. `import-linter` in CI enforces the dependency graph below.

## Dependency graph

```
apps/web ──HTTP──► apps/api ─► services/agent ─► services/context ─► services/ir
                       │              └────────► services/geometry ─► services/ir
                       └──────────────────────────────────────────────► (all four)
```

`services/ir` depends on nothing internal. `geometry` and `context` never import each other or `agent`. `agent` sees `geometry` and `context` only through the protocols below, so tests inject fakes.

## Interfaces

All boundary types are frozen pydantic models. Lengths are stored in mm, angles in degrees; `unit` records the display unit.

### services/ir

```python
class Provenance(BaseModel):   # frozen
    source: Literal["prompt", "document", "rule", "standard", "default", "user_edit", "mesh_fit", "vision"]
    ref: str | None            # doc_id#page:line, rule_id, standard id, message id
    quote: str | None

class Param(BaseModel):
    name: str                  # snake_case id; label is derived for the panel
    value: float | int | str | bool
    unit: str                  # pint unit string, "" for counts
    min: float | None; max: float | None
    description: str
    provenance: Provenance

Expr = str                     # arithmetic over param names, e.g. "base_bolt_spacing_x / 2"

class Sketch(BaseModel):  id, plane, entities: list[Line|Arc|Circle|Point|Spline|Rect|Slot], constraints: list[Constraint]
class Feature(BaseModel): id, name, kind: Literal["extrude","revolve","loft","sweep","hole","fillet","chamfer","shell","pattern_linear","pattern_polar","mirror","boolean","standard_part","airfoil_section"], args: dict[str, Expr | ...], intent: str, provenance: Provenance
class Part(BaseModel):    id, name, material: str | None, features: list[Feature], named_faces: dict[str, FaceSelector]
class Joint(BaseModel):   id, kind: Literal["rigid","revolute","prismatic","cylindrical","fastened"], a: Anchor, b: Anchor
class Design(BaseModel):  title, params: list[Param], sketches, parts: list[Part], joints: list[Joint], version: int

def json_schema(stage: Literal["params", "sketches", "features", "assembly", "full"]) -> dict
def validate(design: Design) -> list[IrError]                  # references, expressions, units, DOF
def compile_design(design: Design) -> str                      # build123d source, deterministic
def apply_params(design: Design, updates: dict[str, float]) -> Design
def diff(a: Design, b: Design) -> DesignDiff
def scope(design: Design, component_id: str) -> Design          # for targeted edits
```

### services/geometry

```python
class Artifact(BaseModel):
    design_hash: str
    files: dict[Literal["step","stl","glb","png","py","ir","fcstd"], Path]
    metrics: Metrics           # volume, area, bbox, mass, cog, solid/face/hole counts per part
    validity: list[Finding]

class Finding(BaseModel):  rule_id, severity: Literal["error","warning"], kind: Literal["static","dynamic"], message, location: FaceSelector | None, suggestion: str | None

class Geometry(Protocol):
    def build(self, design: Design, timeout_s: float) -> Artifact           # runs compiled source in a warm sandboxed worker
    def check_dfm(self, artifact: Artifact, process: Process, rules: RuleSet) -> list[Finding]
    def measure(self, artifact: Artifact, query: MeasureQuery) -> Measurement
    def import_step(self, path: Path) -> Design                             # recognised features where possible, else a "reference body"
    def reconstruct_mesh(self, path: Path) -> Design                        # primitive/feature fitting
    def sensitivities(self, design: Design, metrics: list[str]) -> dict[str, dict[str, float]]
```

Sandbox: worker subprocess, no network, CPU/time limits, only `build123d`/`bd_warehouse`/`math` importable from compiled source.

### services/context

```python
class Fact(BaseModel):      id, kind: Literal["parameter","tolerance","material","requirement","rule","standard","convention"], name, value, unit, tol, text, source: Provenance
class Rule(BaseModel):      id, applies_to, expression, kind: Literal["static","dynamic"], process: Process | None, severity, source: Provenance
class ContextPack(BaseModel): chunks, facts: list[Fact], rules: list[Rule], similar_parts: list[PartRef], conventions: list[Fact]

class Context(Protocol):
    def ingest(self, project_id: str, path: Path) -> Document          # PDF, DOCX, MD, TXT, CSV, XLSX, XML, YAML, PNG/JPG, STEP, STL/OBJ
    def retrieve(self, project_id: str, query: str, k: int) -> ContextPack   # hybrid FTS5 + vector + graph expansion
    def rules(self, project_id: str) -> RuleSet                         # defaults ⊕ project overrides
    def record_generation(self, project_id: str, design: Design, used: list[str]) -> None   # graph links, "Used in"
    def stale(self, project_id: str, changed_fact_ids: list[str]) -> list[str]           # model ids to regenerate
    def graph(self, project_id: str) -> GraphView
```

### services/agent

```python
class LLM(Protocol):
    def chat(self, messages: list[Message], schema: dict | None, images: list[bytes], seed: int) -> str
    def embed(self, texts: list[str]) -> list[list[float]]
# adapters: OllamaLLM (default), OpenAICompatLLM (vLLM / llama.cpp server), FakeLLM (tests)

class Step(BaseModel):  kind: Literal["intent","retrieve","plan","emit","compile","check","critique","repair","done","error"], message, design_hash, thumbnail, findings, elapsed_ms

def generate(req: GenerationRequest, deps: Deps) -> Iterator[Step]     # inputs: prompt, attachments, context ids, process, thinking level, n_variants
def refine(design: Design, instruction: str, target: str | None, deps: Deps) -> Iterator[Step]
def suggest(design: Design, artifact: Artifact, deps: Deps) -> list[Suggestion]
```

Loop: intent → retrieve → staged IR emission (params → sketches → features → assembly, each schema-constrained) → `ir.validate` → `geometry.build` → spec checks (every extracted fact evaluated) → rules + DFM → render + vision critique → repair (≤ `max_repairs`, default 3) → done. Seeded, temperature 0.

### apps/api

Native routes: `POST /projects`, `POST /projects/{id}/context`, `GET /projects/{id}/context`, `POST /projects/{id}/generate`, `POST /models/{id}/refine`, `POST /models/{id}/edit`, `PATCH /models/{id}/params`, `GET /models/{id}/versions`, `POST /models/{id}/versions/{v}/restore`, `GET /models/{id}/export?fmt=step|stl|glb|fcstd`, `GET /jobs/{id}`, `GET /jobs/{id}/events` (SSE), `POST /shares`, `POST /hooks` (webhooks), `POST /batch`.
Reference-compatible aliases under `/api/v1`: `generate`, `modify`, `edit`, `download`, with `X-API-Token` or Bearer auth.

## Milestones and exit criteria

| M | Exit criteria |
|---|---|
| M1 vertical slice | `partwright generate "mounting bracket, 4x M6 holes, 80x60 plate, 5 mm thick"` → valid STEP/STL/GLB + params via local Qwen with ≥1 automatic repair logged; `partwright refine`; eval harness A/B of `qwen3.5:4b` vs 7B on the M1 eval set; CI green |
| M2 context | spec PDF + past STEP + rules doc → graph built → generation cites sources → rule violation caught and repaired → similar past part used as prior |
| M2b grounded eval | 10 cases with spec files (PDF, DOCX, XLSX, YAML, CSV, TXT), rules documents and past STEP parts, each with labelled facts and rules; scored for extraction precision/recall, retrieval fact recall, and generation run prompt-only (spec pasted as text) vs grounded (files in a project) on the same checks, rule compliance and citation correctness; scorecard committed |
| M3 web + API | viewer, param panel with live regen, chat refine, timeline, versions, context browser, API tokens, SSE progress, OpenAPI docs |
| M4 assemblies + vision + mesh | joints and exploded view, sketch/photo/drawing → model, STL → parametric, FCStd feature tree verified headless, sizing XML → aircraft |
| Challenge gate (M4/M5) | `evals/cases/challenge.yaml` (user-submitted manifold prompts, verbatim) must pass: one valid solid, every geometric check, every named parameter, and the 5 % robustness rebuilds. Failing today; it is a required exit criterion for M5 and is reported on every scorecard until it passes |
| M5 parity | every row green with a scripted demo; ≥50 eval specs; fine-tune toy run; `PARITY_REPORT.md`; demo script + GIF |

## Row assignment

Owner = agent that closes the row; milestone = target. "eval" owns the demo-part rows but depends on the producing service.

| Owner | M1 | M2 | M3 | M4 | M5 |
|---|---|---|---|---|---|
| ir | GE-2, PR-1 (model) | CX-10, CD-8 | | GE-3, GE-4, GE-12 | CD-7 |
| geometry | GE-1, VM-6, EX-1, EX-2, EX-3 | VM-1, VM-3, IN-9 (import) | PR-10 | IN-7, IN-8, IN-10, GE-5, AS-2, AS-4, EX-4 (FCStd), CD-4 | EX-8, VM-9 |
| agent | IN-1, GE-7, GE-10, PR-4 | CX-7, VM-2, CD-5 | IN-16, GE-9, GE-13, PR-7 | IN-4, IN-5, IN-6, IN-11, GE-6, PR-5, PR-8, AS-3, VM-10 | |
| context | | IN-2, IN-3, IN-12, IN-13, IN-15, CX-4, CX-8, CX-9, CX-11, VM-5 | CX-1, CX-3, CX-6 | IN-14, CD-6 | CX-12, CX-14 |
| api | | | IN-17, PR-2, PR-9, EX-6, EX-7, AP-1, AP-2, AP-3, AP-4, AP-5, AP-7, CD-1, CD-2, WP-6, WP-7 | AP-9 | AP-6, AP-8, CD-3, WP-12 |
| web | | | CX-2, CX-5, PR-3, VM-4, WP-1, WP-2, WP-3, WP-4, WP-5, WP-8, WP-9, WP-11 | AS-1, PR-6 | WP-10, WP-13 |
| data | | | | | CX-13 |
| eval | DP-2, DP-5, DP-7, DP-21 | VM-7, DP-17 | PF-4 | DP-1, DP-3, DP-6, DP-8, DP-9, DP-10, DP-11, DP-12, DP-13, DP-16, DP-19, DP-20, PF-2, PF-3, PF-5 | GE-8, GE-11, VM-8, DP-4, DP-14, DP-15, DP-18, DP-22, PF-1, PF-6, PF-7, PF-8, WP-14, WP-15 |
| docs | | | | | EX-5 |

Count: 138 rows, each assigned once.

## How sub-agents run

- M1 is built here, sequentially, because every later service depends on the IR contract and the build loop: ir → geometry → agent → CLI → eval harness.
- From M2, each owner works in its own git worktree on `feat/<owner>-m<n>`, against the interfaces above, with fakes for the services it does not own. Writers never share files; `services/ir` changes go through the integrator.
- Integration: review each branch against `AGENTS.md`, run CI and the parity tests for the rows it claims, merge small, update the checklist status.

## Known risks

- A 4B model writing correct IR for non-trivial parts is unproven; staged schemas, few-shot from the procedural generators, validators and repair are the mitigation, and the M1 A/B is the first measurement.
- Hard rows with real risk of partial parity: IN-7/IN-8 (mesh → feature tree), IN-11/DP-9/DP-10 (aircraft from sizing XML), GE-11 (90 % from drawings), PF-1/PF-3 speed on this GPU, CX-13 measurable gain from a toy fine-tune. Shortfalls go to `docs/PARITY_REPORT.md` with numbers.
- Disk: ~14 GB free per drive; model pulls are limited to the four in `SUMMARY.md`.
