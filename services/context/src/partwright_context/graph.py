import itertools
from collections.abc import Sequence

import networkx as nx

from partwright_context.chunking import chunk_of
from partwright_context.entities import Mention, mentions
from partwright_context.models import Chunk, Document, EdgeType, Fact, GraphEdge, GraphNode, GraphView
from partwright_context.parsed import Line
from partwright_ir import Rule

Graph = tuple[list[GraphNode], list[GraphEdge]]


def entity_id(mention: Mention) -> str:
    kind, name = mention
    return f"std:{name}" if kind == "standard" else f"ent:{kind}:{name}"


def entity_node(mention: Mention) -> GraphNode:
    kind, name = mention
    return GraphNode(id=entity_id(mention), type="standard" if kind == "standard" else "entity", name=name, props={"kind": kind})


def document_graph(
    doc: Document, chunks: Sequence[Chunk], facts: Sequence[Fact], rules: Sequence[tuple[str, Rule, Line]], lines: Sequence[Line]
) -> Graph:
    nodes = [GraphNode(id=doc.id, type="document", name=doc.name, doc_id=doc.id, props={"kind": doc.kind, "role": doc.role})]
    edges: list[GraphEdge] = []

    def owner(page: int, line: int) -> str:
        found = chunk_of(chunks, page, line) or next((c for c in chunks if c.page == page), None)
        return found.id if found else doc.id

    def link(src: str, dst: str, type_: EdgeType) -> None:
        edges.append(GraphEdge(src=src, dst=dst, type=type_))

    for c in chunks:
        nodes.append(GraphNode(id=c.id, type="chunk", name=f"{doc.name} p{c.page} l{c.line_start}", doc_id=doc.id, props={"page": c.page}))
        link(doc.id, c.id, "contains")
    for f in facts:
        nodes.append(GraphNode(id=f.id, type="fact", name=f.name, doc_id=doc.id, props={"kind": f.kind, "value": f.value, "unit": f.unit}))
        link(owner(f.page, f.line), f.id, "defines")
    for node_id, rule, line in rules:
        nodes.append(GraphNode(id=node_id, type="rule", name=rule.id, doc_id=doc.id, props={"kind": rule.kind, "value": rule.value}))
        link(owner(line.page, line.number), node_id, "defines")
    for line in lines:
        found = mentions(line.text)
        nodes.extend(entity_node(m) for m in found)
        edges.extend(GraphEdge(src=owner(line.page, line.number), dst=entity_id(m), type="mentions") for m in found)
        edges.extend(GraphEdge(src=entity_id(a), dst=entity_id(b), type="related_to") for a, b in itertools.combinations(sorted(found), 2))
    for f in facts:
        edges.extend(GraphEdge(src=f.id, dst=entity_id(m), type="mentions") for m in mentions(f.text))
    if doc.descriptor is not None:
        props = {"descriptor": doc.descriptor.model_dump(mode="json")}
        nodes.append(GraphNode(id=f"{doc.id}:part", type="part", name=doc.name, doc_id=doc.id, props=props))
        link(doc.id, f"{doc.id}:part", "contains")
    return nodes, edges


def view(nodes: Sequence[GraphNode], edges: Sequence[GraphEdge]) -> GraphView:
    counts: dict[str, int] = {}
    for n in nodes:
        counts[n.type] = counts.get(n.type, 0) + 1
    return GraphView(nodes=list(nodes), edges=list(edges), counts=counts)


def to_networkx(graph: GraphView) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    g.add_nodes_from((n.id, {"type": n.type, "name": n.name, "model_id": n.model_id}) for n in graph.nodes)
    g.add_edges_from((e.src, e.dst, e.type) for e in graph.edges)
    return g


def derived_from(g: nx.MultiDiGraph, node_id: str) -> set[str]:
    if node_id not in g:
        return set()
    derived = nx.subgraph_view(g, filter_edge=lambda _u, _v, key: key == "derived_from")
    return set(nx.ancestors(derived, node_id))
