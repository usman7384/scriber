from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import Connection, Select, delete, func, insert, or_, select

from scriber_context import db, index
from scriber_context.models import Chunk, Document, Fact, GraphEdge, GraphNode
from scriber_ir import Design, Rule


def check_meta(conn: Connection, key: str, value: str) -> None:
    stored = conn.execute(select(db.meta.c.value).where(db.meta.c.key == key)).scalar()
    if stored is None:
        conn.execute(insert(db.meta).values(key=key, value=value))
    elif stored != value:
        raise ValueError(f"project index was built with {key}={stored}, not {value}")


def save_document(
    conn: Connection, doc: Document, chunks: Sequence[Chunk], facts: Sequence[Fact], rules: Sequence[tuple[str, Rule]]
) -> None:
    seq = (conn.execute(select(func.max(db.documents.c.seq))).scalar() or 0) + 1
    conn.execute(insert(db.documents).values(id=doc.id, seq=seq, data=doc.model_dump(mode="json")))
    if chunks:
        conn.execute(insert(db.chunks), [{"id": c.id, "doc_id": c.doc_id, "data": c.model_dump(mode="json")} for c in chunks])
    if facts:
        conn.execute(insert(db.facts), [{"id": f.id, "doc_id": f.doc_id, "kind": f.kind, "data": f.model_dump(mode="json")} for f in facts])
    if rules:
        rows = [{"node_id": n, "rule_id": r.id, "doc_id": doc.id, "seq": seq, "data": r.model_dump(mode="json")} for n, r in rules]
        conn.execute(insert(db.rules), rows)


def save_graph(conn: Connection, nodes: Iterable[GraphNode], edges: Iterable[GraphEdge]) -> None:
    existing = set(conn.execute(select(db.nodes.c.id)).scalars())
    new_nodes = {n.id: n for n in nodes if n.id not in existing}
    if new_nodes:
        conn.execute(insert(db.nodes), [n.model_dump(mode="json") for n in new_nodes.values()])
    present = {(e.src, e.dst, e.type) for e in all_edges(conn)}
    new_edges = {(e.src, e.dst, e.type) for e in edges} - present
    if new_edges:
        conn.execute(insert(db.edges), [{"src": s, "dst": d, "type": t} for s, d, t in sorted(new_edges)])


def delete_document(conn: Connection, doc_id: str) -> None:
    if conn.execute(select(db.documents.c.id).where(db.documents.c.id == doc_id)).first() is None:
        raise KeyError(f"unknown document {doc_id}")
    chunk_ids = list(conn.execute(select(db.chunks.c.id).where(db.chunks.c.doc_id == doc_id)).scalars())
    part_ids = list(conn.execute(select(db.nodes.c.id).where(db.nodes.c.doc_id == doc_id, db.nodes.c.type == "part")).scalars())
    index.remove(conn, chunk_ids, part_ids)
    delete_nodes(conn, list(conn.execute(select(db.nodes.c.id).where(db.nodes.c.doc_id == doc_id)).scalars()))
    conn.execute(delete(db.documents).where(db.documents.c.id == doc_id))
    for table in (db.chunks, db.facts, db.rules):
        conn.execute(delete(table).where(table.c.doc_id == doc_id))
    mentioned = select(db.edges.c.dst).where(db.edges.c.type == "mentions")
    orphans = select(db.nodes.c.id).where(db.nodes.c.type.in_(["entity", "standard"]), ~db.nodes.c.id.in_(mentioned))
    delete_nodes(conn, list(conn.execute(orphans).scalars()))


def delete_nodes(conn: Connection, ids: list[str]) -> None:
    if ids:
        conn.execute(delete(db.edges).where(or_(db.edges.c.src.in_(ids), db.edges.c.dst.in_(ids))))
        conn.execute(delete(db.nodes).where(db.nodes.c.id.in_(ids)))


def documents(conn: Connection) -> list[Document]:
    rows = conn.execute(select(db.documents.c.data).order_by(db.documents.c.seq)).scalars()
    return [Document.model_validate(r) for r in rows]


def chunks(conn: Connection, ids: Sequence[str]) -> list[Chunk]:
    found = {r["id"]: Chunk.model_validate(r) for r in conn.execute(select(db.chunks.c.data).where(db.chunks.c.id.in_(ids))).scalars()}
    return [found[i] for i in ids if i in found]


def facts(conn: Connection, ids: Sequence[str] | None = None, doc_ids: Sequence[str] | None = None) -> list[Fact]:
    query = select(db.facts.c.data)
    if ids is not None:
        query = query.where(db.facts.c.id.in_(ids))
    if doc_ids is not None:
        query = query.where(db.facts.c.doc_id.in_(doc_ids))
    found = [Fact.model_validate(r) for r in conn.execute(query).scalars()]
    return sorted(found, key=lambda f: (f.doc_id, f.page, f.line, f.id))


def active_rules(conn: Connection) -> dict[str, tuple[str, Rule]]:
    rows = conn.execute(select(db.rules.c.node_id, db.rules.c.data).order_by(db.rules.c.seq, db.rules.c.node_id))
    out: dict[str, tuple[str, Rule]] = {}
    for node_id, data in rows:
        rule = Rule.model_validate(data)
        out[rule.id] = (node_id, rule)
    return out


def set_rule(conn: Connection, rule: Rule) -> None:
    node_id = f"user:{rule.id}"
    seq = (conn.execute(select(func.max(db.rules.c.seq))).scalar() or 0) + 1
    conn.execute(delete(db.rules).where(db.rules.c.node_id == node_id))
    conn.execute(insert(db.rules).values(node_id=node_id, rule_id=rule.id, doc_id=None, seq=seq, data=rule.model_dump(mode="json")))


def all_nodes(conn: Connection) -> list[GraphNode]:
    rows = conn.execute(select(db.nodes).order_by(db.nodes.c.id)).mappings()
    return [GraphNode.model_validate(dict(r)) for r in rows]


def all_edges(conn: Connection) -> list[GraphEdge]:
    rows = conn.execute(select(db.edges).order_by(db.edges.c.src, db.edges.c.dst, db.edges.c.type)).mappings()
    return [GraphEdge.model_validate(dict(r)) for r in rows]


def save_design(conn: Connection, model_id: str, design: Design) -> None:
    old = conn.execute(select(db.nodes.c.id, db.nodes.c.type).where(db.nodes.c.model_id == model_id)).all()
    index.remove(conn, [], [i for i, t in old if t == "part"])
    delete_nodes(conn, [i for i, _ in old])
    conn.execute(delete(db.designs).where(db.designs.c.model_id == model_id))
    conn.execute(insert(db.designs).values(model_id=model_id, data=design.model_dump(mode="json")))


def designs(conn: Connection) -> dict[str, Design]:
    rows = conn.execute(select(db.designs.c.model_id, db.designs.c.data))
    return {model_id: Design.model_validate(data) for model_id, data in rows}


def targets(conn: Connection, sources: Sequence[str], type_: str) -> list[str]:
    query = select(db.edges.c.dst).where(db.edges.c.src.in_(sources), db.edges.c.type == type_).order_by(db.edges.c.dst)
    return list(conn.execute(query).scalars())


def parts(conn: Connection) -> list[GraphNode]:
    rows = conn.execute(select(db.nodes).where(db.nodes.c.type == "part").order_by(db.nodes.c.id)).mappings()
    return [GraphNode.model_validate(dict(r)) for r in rows]


def counts(conn: Connection) -> dict[str, int]:
    def count(query: Select[Any]) -> int:
        return int(conn.execute(query).scalar() or 0)

    used = select(func.count(func.distinct(db.edges.c.src))).where(
        db.edges.c.type == "used_in", db.edges.c.src.in_(select(db.documents.c.id))
    )
    return {
        "files": count(select(func.count()).select_from(db.documents)),
        "facts": count(select(func.count()).select_from(db.facts)),
        "rules": count(select(func.count(func.distinct(db.rules.c.rule_id)))),
        "entities": count(select(func.count()).select_from(db.nodes).where(db.nodes.c.type.in_(["entity", "standard"]))),
        "relations": count(select(func.count()).select_from(db.edges)),
        "generations": count(select(func.count()).select_from(db.designs)),
        "used_in_generation": count(used),
    }
