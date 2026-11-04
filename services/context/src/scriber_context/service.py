import hashlib
import math
import re
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import Engine

from scriber_context import index, store
from scriber_context.defaults import DEFAULT_RULES
from scriber_context.embed import Embedder
from scriber_context.extract import process
from scriber_context.graph import derived_from, document_graph, to_networkx, view
from scriber_context.lineage import generation_graph, resolve
from scriber_context.models import ContextPack, Document, Fact, GraphNode, GraphView, KbStats
from scriber_context.proposals import Propose
from scriber_context.readers import Describe
from scriber_context.retrieval import fuse, similar_parts
from scriber_ir import Design, Rule, RuleSet, ShapeDescriptor

PROJECT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class LocalContext:
    def __init__(
        self,
        data_dir: Path,
        embedder: Embedder,
        describe: Describe | None = None,
        propose: Propose | None = None,
        defaults: RuleSet = DEFAULT_RULES,
    ) -> None:
        self._data_dir = data_dir
        self._embedder = embedder
        self._describe = describe
        self._propose = propose
        self._defaults = defaults
        self._engines: dict[str, Engine] = {}

    def __enter__(self) -> "LocalContext":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()

    def ingest(self, project_id: str, path: Path) -> Document:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        existing = next((d for d in self.documents(project_id) if d.sha256 == digest), None)
        if existing is not None:
            return existing
        x = process(path, digest, self._describe, self._propose)
        vectors = self._embedder.embed([c.text for c in x.chunks])
        with self._engine(project_id).begin() as conn:
            store.save_document(conn, x.doc, x.chunks, x.facts, [(n, r) for n, r, _ in x.rules])
            store.save_graph(conn, *document_graph(x.doc, x.chunks, x.facts, x.rules, x.parsed.lines))
            index.add_chunks(conn, [(c.id, c.text, v) for c, v in zip(x.chunks, vectors, strict=True)])
            if x.doc.descriptor is not None:
                index.add_part(conn, f"{x.doc.id}:part", vectors[0])
        return x.doc

    def retrieve(self, project_id: str, query: str, k: int = 8, shape: ShapeDescriptor | None = None) -> ContextPack:
        vector = self._embedder.embed([query])[0]
        with self._engine(project_id).connect() as conn:
            ids = fuse([index.keyword(conn, query, 4 * k), index.nearest(conn, vector, 4 * k)])[:k]
            linked = set(store.targets(conn, ids, "defines"))
            conventions = [d.id for d in store.documents(conn) if d.role == "convention"]
            return ContextPack(
                query=query,
                chunks=store.chunks(conn, ids),
                facts=store.facts(conn, ids=sorted(linked)),
                rules=[rule for node_id, rule in store.active_rules(conn).values() if node_id in linked],
                similar_parts=similar_parts(store.parts(conn), index.part_vectors(conn), store.designs(conn), vector, shape, k),
                conventions=store.facts(conn, doc_ids=conventions),
            )

    def rules(self, project_id: str) -> RuleSet:
        with self._engine(project_id).connect() as conn:
            project = RuleSet(rules=[rule for _, rule in store.active_rules(conn).values()])
        return self._defaults.merged(project)

    def set_rule(self, project_id: str, rule: Rule) -> None:
        with self._engine(project_id).begin() as conn:
            store.set_rule(conn, rule)

    def record_generation(
        self, project_id: str, model_id: str, design: Design, used: list[str], shapes: Mapping[str, ShapeDescriptor] | None = None
    ) -> None:
        vectors = self._embedder.embed([f"{design.title} {p.name} {p.material or ''}" for p in design.parts])
        with self._engine(project_id).begin() as conn:
            store.save_design(conn, model_id, design)
            known = {n.id: n for n in store.all_nodes(conn)}
            rules = {r.id: (f"default:{r.id}", r) for r in self._defaults.rules} | store.active_rules(conn)
            used_ids = resolve(used, known, rules)
            fresh = [GraphNode(id=u, type="rule", name=u.removeprefix("default:")) for u in dict.fromkeys(used_ids) if u not in known]
            known |= {n.id: n for n in fresh}
            nodes, edges = generation_graph(model_id, design, used_ids, store.facts(conn), known, shapes or {})
            store.save_graph(conn, [*fresh, *nodes], edges)
            for part, vector in zip(design.parts, vectors, strict=True):
                index.add_part(conn, f"{model_id}/{part.id}", vector)

    def stale(self, project_id: str, changed_fact_ids: list[str]) -> list[str]:
        g = to_networkx(self.graph(project_id))
        models = {g.nodes[n]["model_id"] for fact_id in changed_fact_ids for n in derived_from(g, fact_id)}
        return sorted(m for m in models if m)

    def changed(self, project_id: str, old_doc_id: str, new_doc_id: str) -> list[str]:
        revised = {_signature(f) for f in self.facts(project_id, new_doc_id)}
        return [f.id for f in self.facts(project_id, old_doc_id) if _signature(f) not in revised]

    def graph(self, project_id: str) -> GraphView:
        with self._engine(project_id).connect() as conn:
            return view(store.all_nodes(conn), store.all_edges(conn))

    def stats(self, project_id: str) -> KbStats:
        with self._engine(project_id).connect() as conn:
            c = store.counts(conn)
        score = 10 * c["files"] + 2 * c["facts"] + 5 * c["rules"] + 20 * c["used_in_generation"]
        level = math.isqrt(score // 100)
        return KbStats(**c, score=score, level=level, next_level_score=100 * (level + 1) ** 2)

    def documents(self, project_id: str) -> list[Document]:
        with self._engine(project_id).connect() as conn:
            return store.documents(conn)

    def facts(self, project_id: str, doc_id: str | None = None) -> list[Fact]:
        with self._engine(project_id).connect() as conn:
            return store.facts(conn, doc_ids=None if doc_id is None else [doc_id])

    def delete_document(self, project_id: str, doc_id: str) -> None:
        with self._engine(project_id).begin() as conn:
            store.delete_document(conn, doc_id)

    def _engine(self, project_id: str) -> Engine:
        if not PROJECT_ID.fullmatch(project_id):
            raise ValueError(f"invalid project id {project_id!r}")
        if project_id not in self._engines:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            engine = index.open_engine(self._data_dir / f"{project_id}.sqlite", self._embedder.dim)
            with engine.begin() as conn:
                store.check_meta(conn, "embedder", f"{self._embedder.name}/{self._embedder.dim}")
            self._engines[project_id] = engine
        return self._engines[project_id]


def _signature(f: Fact) -> tuple[object, ...]:
    return (f.kind, f.name, f.value, f.unit, f.tol, f.count, f.at)
