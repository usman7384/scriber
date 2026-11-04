# Context service (M2)

Branch `feat/context-m2`. New package `services/context` (`scriber-context`, import `scriber_context`). It turns uploaded engineering files into cited facts, rules and a per-project knowledge graph, and returns a `ContextPack` for generation.

## What exists

| Module | Job |
|---|---|
| `readers.py`, `pdf.py`, `office.py`, `plain.py` | PDF (pypdfium2 text per page and line, pdfplumber ruled tables), DOCX (paragraphs and tables in document order), MD/TXT (Markdown tables become rows), CSV, XLSX (one page per sheet), XML (expat, element path and source line), YAML (composed nodes, source line), images (stored, no text), STEP/STL/OBJ through an injected `describe: Callable[[Path], ShapeDescriptor]` |
| `quantities.py`, `facts.py`, `tables.py`, `entities.py` | Deterministic extraction: quantities with pint (lengths in mm, angles in deg, N, kg, MPa, N*m), symmetric and asymmetric tolerances, hole callouts (`4×M6`, `4x M6`, `6 x Ø6.6`), size chains (`200 × 120 × 5 mm`), `key: value` / `key = value`, materials gazetteer, ISO/DIN/EN/ASME/ANSI standards, hole tables (x, y, Ø) |
| `rule_text.py`, `defaults.py` | Sentence assembly across wrapped lines and rule extraction into `scriber_ir.Rule` for the six `RuleKind`s; default rule set |
| `proposals.py`, `extract.py` | Optional LLM pass through an injected `propose(chunk_text) -> list[ProposedFact]`; a proposal is kept only if its quote is in the chunk and its number is in the quote |
| `chunking.py`, `embed.py` | Chunks with page and line span; `Embedder` protocol, `OllamaEmbedder` (`qwen3-embedding:0.6b`), `HashEmbedder` for tests |
| `db.py`, `store.py`, `index.py` | One SQLite file per project under the injected data directory |
| `graph.py`, `lineage.py` | Document graph, generation lineage, networkx view, `derived_from` traversal |
| `retrieval.py`, `shapes.py` | Reciprocal-rank fusion, similar parts by descriptor distance and text similarity |
| `service.py`, `protocol.py` | `LocalContext` and the `Context` protocol |

## Public API

```python
LocalContext(data_dir: Path, embedder: Embedder, describe: Describe | None = None, propose: Propose | None = None, defaults: RuleSet = DEFAULT_RULES)
ingest(project_id, path) -> Document
retrieve(project_id, query, k=8, shape: ShapeDescriptor | None = None) -> ContextPack   # chunks, facts, rules, similar_parts, conventions
rules(project_id) -> RuleSet                       # DEFAULT_RULES.merged(project rules)
set_rule(project_id, rule: Rule) -> None           # user/project override
record_generation(project_id, model_id, design, used: list[str], shapes: Mapping[part_id, ShapeDescriptor] | None = None) -> None
stale(project_id, changed_fact_ids) -> list[str]   # model ids
graph(project_id) -> GraphView                     # nodes, edges, counts; to_networkx(view), derived_from(g, node_id)
stats(project_id) -> KbStats
documents(project_id) -> list[Document]
facts(project_id, doc_id=None) -> list[Fact]
delete_document(project_id, doc_id) -> None
```

```python
with LocalContext(Path("data/context"), OllamaEmbedder(), describe=geometry_describe) as ctx:
    doc = ctx.ingest("proj", Path("requirements.pdf"))
    pack = ctx.retrieve("proj", "bracket with 4 M6 holes and an 82 mm bore", k=8)
    rules = ctx.rules("proj").for_process("milling_3axis")
    ctx.record_generation("proj", "model-7", design, used=[doc.id, *(f.id for f in pack.facts)])
```

Changes against `docs/PLAN.md`: `record_generation` takes a `model_id` (the plan's has none, but `stale` must return model ids) and optional part descriptors so generated parts can be found as similar parts; `retrieve` takes an optional `shape` for descriptor ranking; `set_rule`, `documents`, `facts`, `stats` and `delete_document` are added. `Rule` is the IR's `Rule`, not the plan's draft. `Fact` has `tol` as `(lower, upper)` deviations, `count` for callouts, `at` for hole-table positions and `page`/`line`; kinds are `parameter`, `tolerance`, `holes`, `hole`, `material`, `standard`. Team conventions are facts from documents whose name or first line reads as best practice or conventions (`Document.role == "convention"`); they join every pack.

## Decisions

- **Storage: SQLAlchemy Core over SQLite.** D-008 asks for Postgres readiness, and Core gives portable DDL, typed queries and JSON columns without an ORM. Everything SQLite-only (engine URL, loading the `sqlite-vec` extension, the FTS5 table `chunk_text`, the vec0 tables `chunk_vec` and `part_vec`) is in `index.py`; on Postgres that module becomes `tsvector` plus pgvector. Re-ingest and replace use delete and insert, so no dialect upsert. Each project file records its embedder name and dimension and refuses another one.
- **Ids.** Document `d` + 12 hex chars of the file's SHA-256 (re-uploading the same bytes is a no-op); chunk `<doc>:c<n>`; fact `<doc>:<page>.<line>.<i>` (`.h<n>` for hole-table rows, `.llm<i>` for proposals); every fact and rule carries `Provenance(source="document", ref="<doc>#p<page>:l<line>", quote=...)`. Line numbers are source lines for text, CSV, YAML and XML, text lines per page for PDF, row numbers per sheet for XLSX, and block numbers for DOCX (which has no pages).
- **Extraction is deterministic first.** Regex plus pint never invents a number; the LLM pass can only add facts that are quoted and numerically grounded in the chunk. Fact names come from the key of a `key: value` line, else from up to three content words before the value; requirement ids such as `REQ-2` prefix the name (`req_2_bore`).
- **Rules.** A sentence becomes a rule when it has rule wording (minimum, at least, must, should, not exceed, ...) and a value of the right dimension. `binding` is `dynamic` (severity warning) when the wording is soft (should, recommended, preferably, avoid, ...) and `static` (error) otherwise. `process` comes from milling/CNC/machining, SLA/resin, SLS/powder, FDM/FFF/3D print. Rule id is `kind` or `kind@process`, the same scheme as `DEFAULT_RULES`, so a project document or `set_rule` replaces the default with the same id through `RuleSet.merged`; within a project the most recently ingested rule wins.
- **Graph vocabulary.** Nodes: document, chunk, fact, rule, standard, entity (material, designation such as `KMM-28`, fastener such as `M3`), part (uploaded CAD or generated), feature, parameter. Edges: `contains`, `defines` (chunk to fact or rule), `mentions`, `related_to` (entities named on the same line), `constrains` (rule to part), `derived_from`, `used_in`.
- **Lineage.** A parameter derives from the fact, chunk or document its `provenance.ref` names (a fact id, a node id, or a `doc#p:l` ref resolved to the facts on that line, preferring the one with the same value); without a usable ref it derives from facts of the used documents with the same value and unit (or the same callout count for unitless params). A feature derives from every parameter its expressions (and its sketch's) reference, and from its own provenance ref. Used ids may be document, chunk, fact or rule node ids, or rule ids (`min_hole_edge_ratio`, also defaults). Documents, facts and chunks get `used_in` to each part, rules get `constrains`; the part `mentions` every entity named in the design text or in the facts it derives from. `stale` walks `derived_from` edges backwards from the changed ids and returns the model ids it reaches.
- **Retrieval.** FTS5 BM25 and vector KNN (4k each) fused by reciprocal rank (c = 60), top k chunks, then one hop of `defines` edges to facts and active rules. Similar parts score the cosine between query and part text, averaged with `1 / (1 + d)` when a query descriptor is given, where `d` is the mean log ratio of sorted bounding-box sides plus a third of the log volume ratio plus the share of hole diameters not in common.
- **Knowledge-base level (CX-6).** `score = 10·files + 2·facts + 5·rules + 20·used_in_generation`, where `rules` counts distinct project rule ids and `used_in_generation` counts documents with at least one `used_in` edge; `level = floor(sqrt(score / 100))` (integer division first), `next_level_score = 100·(level + 1)²`. So level 1 starts at 100 points, level 2 at 400, level 3 at 900.

## Dependencies added

`pypdfium2==5.14.0` (Apache-2.0 / BSD-3), `pdfplumber==0.11.10` (MIT; pulls `pdfminer.six` MIT and `cryptography` Apache-2.0/BSD), `python-docx==1.2.0` (MIT; `lxml` BSD), `openpyxl==3.1.5` (MIT), `pyyaml==6.0.3` (MIT), `pint==0.26.2` (BSD-3), `networkx==3.7` (BSD-3), `sqlalchemy==2.1.6` (MIT), `sqlite-vec==0.1.9` (MIT / Apache-2.0), `ollama==0.6.3` (MIT), `pydantic==2.14.1` (MIT). No PDF writer: test PDFs are written by a 40-line generator in `tests/conftest.py`.

## Rows advanced (context side) and evidence

All in `services/context/tests`. None is done: each still needs the generation side and the scripted demo.

| Row | Test |
|---|---|
| IN-2 | `test_context.py::test_hole_tables_from_markdown_csv_and_xlsx_agree` (plate_spec.md: 10 holes with positions), `test_facts.py::test_size_chain_becomes_three_axis_facts` |
| IN-3 | `test_context.py::test_hole_tables_from_markdown_csv_and_xlsx_agree` (CSV and XLSX give identical hole facts) |
| IN-9 | `test_readers.py::test_cad_files_use_the_injected_describer`, `test_context.py::test_similar_parts_rank_uploaded_cad_by_shape` |
| IN-12 | `test_context.py::test_requirements_are_retrieved_traced_to_features_and_marked_stale` (4×M6 and Ø82 ±0.2 from a PDF, REQ to feature links) |
| IN-13 | `test_context.py::test_rule_documents_feed_rules_and_retrieval`, `test_rule_text.py::test_rule_sentences` |
| IN-15 | `test_context.py::test_report_values_are_cited` (3.2 mm cited to the report's page and line) |
| CX-1 | `test_context.py::test_six_file_types_are_listed_as_processed` (no per-file progress events; that is the API/web part) |
| CX-3 | `test_context.py::test_entities_relations_and_generated_part_links` (`used_in` is exactly the two documents passed) |
| CX-4 | `test_context.py::test_entities_relations_and_generated_part_links` (KMM-28 `related_to` M3; generated part mentions both) |
| CX-6 | `test_context.py::test_stats_follow_the_documented_formula` |
| CX-8 | `test_context.py::test_conventions_join_every_pack` |
| CX-9 | `test_facts.py` (Ø82 ±0.2 mm as `{name, value, unit, tol, source}`, 4×M6 / 4x M6, materials, standards, key/value) |
| CX-11 | `test_context.py::test_requirements_are_retrieved_traced_to_features_and_marked_stale` (features derived from REQ-3; `stale` returns only the model that used it) |
| VM-5 | `test_context.py::test_rule_overrides_are_per_project` (1.5 → 2.0 by document and 1.9 by `set_rule`; an 18 mm edge on Ø10 flags only where overridden) |

## Known gaps

- No OCR: scanned PDFs and images give no text. No ISO 286 fits, roughness, `R2` radii or ranges in the tagger. A bare `in` after a number is read as inches.
- Hole-to-edge rules stated as an absolute distance are not representable (`min_hole_edge_ratio` only); they stay as text in chunks. Sentences with two rule kinds yield the first matching kind.
- PDF tables need ruling lines (pdfplumber default strategy); their rows are mapped to the first page line holding all cells.
- A changed file is a new document; computing which facts changed between versions (input to `stale`) is left to the caller. Deleting a document drops the lineage edges into it, and `related_to` edges survive while both entities are still mentioned elsewhere.
- Hole-table facts link to features only through parameters or provenance, not by matching coordinates in point lists.
- The `@pytest.mark.llm` test (`test_ollama_embed.py`) was not run: `OllamaEmbedder` passes `dimensions=1024` and its behaviour with `qwen3-embedding:0.6b` is unverified.
- No IR change was needed. `Part` and `Feature` are not exported from `scriber_ir`, so `lineage.py` works on `design.parts[i]` instead of naming the type; exporting them would simplify it.
