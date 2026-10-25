# Per-project knowledge graph and retrieval

Researched 2026-10-25. "Verified" means the package was installed and run on Windows Python 3.11 today.

## TL;DR

- **Graph store: SQLite-backed property graph** (a `nodes` and an `edges` table with JSON props and recursive CTEs), one `project.sqlite` per project. Load the graph into **networkx 3.6.1** in memory for algorithms (neighbourhoods, shortest paths, impact analysis). There is no server and nothing new to install, and it is trivially backed up.
- **Vectors: `sqlite-vec` 0.1.9** in the same SQLite file. Verified on Windows: the extension loads into stdlib `sqlite3` 3.45.1, and `vec0` KNN returned correct neighbours. Add **FTS5** for BM25 to get hybrid search in one file.
- **Kùzu is archived.** The repo was archived on 10 Oct 2025 after Apple acquired Kùzu Inc, and 0.11.3 is the final release ([The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/), [dbdb.io](https://dbdb.io/db/ladybugdb)). The community fork **LadybugDB** (MIT) is active, but its packaging on Windows is unstable today. Do not adopt it now. Keep the graph layer behind an interface so it can be swapped in later if Cypher or scale is needed.

## Graph store options

| | SQLite property graph (+ networkx) | Kùzu 0.11.3 | LadybugDB (Kùzu fork) | Neo4j Community | networkx only |
|---|---|---|---|---|---|
| Licence | public domain / BSD-3 | MIT | MIT | **GPL-3.0** server (driver Apache-2.0) | BSD-3 |
| Status | stable | **archived Oct 2025**, no fixes | active (fork, ~1.9k stars) | active | stable |
| Embedded | yes | yes | yes | no (JVM server, Docker) | in-memory only |
| Windows | stdlib | wheel works (**verified**) | `real-ladybug` 0.15.3 works (**verified**: create, insert, Cypher MATCH). **`ladybug` 0.22.0 fails** with `DLL load failed while importing _lbug` (**verified**) | Docker / JVM install | yes |
| Query | SQL + recursive CTE | Cypher | Cypher | Cypher | Python |
| Footprint | 0 | ~30 MB | ~30 MB | ~500 MB+ RAM, JVM | 0 |
| Vectors in the same store | sqlite-vec | built-in extension | built-in extension | Neo4j vector index | no |
| Verdict | **choose** | no (dead) | revisit in 6 months | no (GPL server, heavy, not local-first) | use as the compute layer |

A per-project engineering graph is small: roughly 10³–10⁵ nodes. SQLite with indexes on `(src, type)` and `(dst, type)` handles 2–3-hop expansions in milliseconds. Cypher's ergonomics are not worth the dependency risk.

## Schema (typed, closed vocabulary)

```
nodes(id TEXT PK, type TEXT, name TEXT, props JSON, project_rev INT, created_at, updated_at)
edges(id TEXT PK, src TEXT, dst TEXT, type TEXT, props JSON, provenance JSON)  -- idx(src,type), idx(dst,type)
chunks(id PK, doc_id, page, bbox JSON, section, text, kind)                  -- + FTS5 virtual table
vec_chunks USING vec0(embedding float[1024])                                  -- qwen3-embedding:0.6b dim (verify; Matryoshka-truncatable)
```

| Node types | Edge types |
|---|---|
| Document, Chunk, Requirement, Rule, Standard (ISO 4762, ISO 273…), Material, Process (CNC-3ax, FDM, SLS, sheet), Part, Assembly, Sketch, Feature, Parameter, Joint, StandardPart (fastener, bearing), Revision | `CONTAINS` (Doc→Chunk), `MENTIONS` (Chunk→any), `DERIVED_FROM` (any→Chunk, provenance), `HAS_PART`, `HAS_FEATURE`, `HAS_PARAM`, `CONSTRAINS` (Rule/Requirement→Parameter/Feature/Part), `CITES` (Rule→Standard), `APPLIES_TO` (Rule→Material/Process/Part-tag), `USES_MATERIAL`, `MADE_BY` (Part→Process), `CONNECTS` (Joint→Part ×2), `INSTANCE_OF` (Part→StandardPart), `SUPERSEDES` (Revision), `CONFLICTS_WITH` (Rule↔Rule) |

IR parameters carry `provenance: [{node_id, chunk_id, quote}]`, so every number in a model can answer "where did this come from?"

## Entity and relation extraction with small local LLMs

Open-ended triple extraction (GraphRAG style) with a 4B model is too noisy. Use a **closed-schema, two-stage** extractor:

1. **Deterministic pass:** the dimension/tolerance tagger (see `doc-parsing.md`), plus a gazetteer and regex for standards (`(ISO|DIN|EN|ASME|ANSI)\s?\d+(-\d+)?`), metric threads, and materials (a seed list: 6061-T6, 7075, S235, 1.4301/304, PA12, PLA, PETG, ABS, POM…), plus process keywords. This gives high precision and no GPU use.
2. **LLM pass (`qwen3.5:4b`, `format` = schema, `think:false`):** per chunk, given the pre-tagged entities, output only **relations among known entity IDs** and `DesignRule` objects. Constraining it to IDs prevents hallucinated entities.
3. **Entity resolution:** normalise (case, whitespace, "DIN 912" ↔ "ISO 4762" alias table, material designation aliases), then exact-match merge. Optionally add an embedding-similarity merge with a confirm step in the UI.
4. Cost: about 1–3 s per chunk on the 4B model (estimate). A 50-page spec is a few minutes as a background job, so it is incremental and resumable.

## Graph-augmented retrieval for generation

```
user prompt / current IR
 ├─ entity-link: tagger + gazetteer over the prompt → seed nodes (part tags, materials, standards)
 ├─ hybrid chunk search: FTS5 BM25 ∪ sqlite-vec KNN (k=20) → reciprocal-rank fusion → top 8
 ├─ graph expansion from seeds + chunk MENTIONS, 1–2 hops on typed edges:
 │     Rule APPLIES_TO {material, process} · Requirement CONSTRAINS Part · StandardPart rows
 └─ context pack (budget ≈ 6k of 16k tokens): accepted Rules (structured) > Requirements > table rows > chunks,
    each with a citation id → the model must cite ids in IR provenance fields
```

- Accepted rules are also enforced **outside** the LLM by the rule checker, so retrieval misses degrade guidance but not safety.
- Embedding model: `qwen3-embedding:0.6b` (639 MB, 32k context, Apache-2.0) through Ollama `/api/embed`. CI uses a deterministic hash embedder.

## Vector store options

| | sqlite-vec 0.1.9 | LanceDB 0.40.0 | Chroma 1.5.9 | FAISS (faiss-cpu 1.15.1) |
|---|---|---|---|---|
| Licence | MIT / Apache-2.0 | Apache-2.0 | Apache-2.0 | MIT |
| Embedded, single file | **yes (same DB as the graph)** | directory of Lance files | directory + SQLite | index file only, no metadata |
| Deps | ~1 MB extension | pyarrow (~100 MB+) | heavy (onnxruntime, etc.) | numpy |
| Windows | **verified** | installed fine (not exercised) | yes | yes |
| ANN | brute force (fine to ~10⁵–10⁶ vectors); quantisation available | IVF-PQ, plus full-text search | HNSW | everything |
| Verdict | **choose** | alternative if we outgrow it | no | no (no metadata/persistence story) |

Caveat: sqlite-vec is still 0.1.x (pre-1.0). Pin it, and keep a small `VectorIndex` interface.
