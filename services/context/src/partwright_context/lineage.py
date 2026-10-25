import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from partwright_context.graph import Graph
from partwright_context.models import EdgeType, Fact, GraphEdge, GraphNode
from partwright_ir import Design, Param, Rule, ShapeDescriptor

NOT_EXPRESSIONS = {"id", "name", "intent", "kind", "provenance"}


@dataclass(frozen=True, slots=True)
class Known:
    facts: Mapping[str, Fact]
    nodes: Mapping[str, GraphNode]

    def sources(self, ref: str | None, param: Param | None = None) -> list[str]:
        if ref is None:
            return []
        if ref in self.facts or ref in self.nodes:
            return [ref]
        cited = [f for f in self.facts.values() if f.source.ref == ref]
        return [f.id for f in [f for f in cited if param is not None and _matches(f, param)] or cited]


def resolve(used: Sequence[str], known: Mapping[str, GraphNode], rules: Mapping[str, tuple[str, Rule]]) -> list[str]:
    missing = [u for u in used if u not in known and u not in rules]
    if missing:
        raise KeyError(f"unknown context ids {missing}")
    return [u if u in known else rules[u][0] for u in used]


def generation_graph(
    model_id: str,
    design: Design,
    used: Sequence[str],
    facts: Sequence[Fact],
    nodes: Mapping[str, GraphNode],
    shapes: Mapping[str, ShapeDescriptor],
) -> Graph:
    known = Known({f.id: f for f in facts}, nodes)
    used_docs = {nodes[u].doc_id for u in used if nodes[u].doc_id}
    pool = [f for f in facts if f.id in used or f.doc_id in used_docs]
    params = {p.name: f"{model_id}/param/{p.name}" for p in design.params}
    out_nodes = [GraphNode(id=params[p.name], type="parameter", name=p.name, model_id=model_id) for p in design.params]
    out_edges = [
        _edge(params[p.name], s, "derived_from") for p in design.params for s in known.sources(p.provenance.ref, p) or _by_value(pool, p)
    ]
    for index, part in enumerate(design.parts):
        part_id = f"{model_id}/{part.id}"
        out_nodes.append(_part_node(part_id, model_id, design, index, shapes.get(part.id)))
        features, feature_edges = _features(part_id, model_id, design, index, params, known)
        out_nodes += features
        out_edges += [_edge(part_id, p, "contains") for p in params.values()] + feature_edges
        derived = sorted({e.dst for e in out_edges if e.type == "derived_from" and e.dst in known.facts})
        docs = sorted({known.facts[d].doc_id for d in derived})
        out_edges += [_edge(u, part_id, "constrains" if nodes[u].type == "rule" else "used_in") for u in [*used, *docs]]
        text = " ".join([_design_text(design, index), *(known.facts[d].text for d in derived)])
        out_edges += [
            _edge(part_id, n.id, "mentions") for n in nodes.values() if n.type in ("entity", "standard") and _mentions(text, n.name)
        ]
    return out_nodes, out_edges


def _features(part_id: str, model_id: str, design: Design, index: int, params: Mapping[str, str], known: Known) -> Graph:
    part = design.parts[index]
    sketches = {s.id: s.model_dump() for s in part.sketches}
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    for feature in part.features:
        feature_id = f"{part_id}/{feature.id}"
        nodes.append(GraphNode(id=feature_id, type="feature", name=feature.name, model_id=model_id, props={"kind": feature.kind}))
        data = {k: v for k, v in feature.model_dump().items() if k not in NOT_EXPRESSIONS}
        uses = sorted(_names([data, sketches.get(data.get("sketch", ""), {})]) & params.keys())
        edges += [_edge(part_id, feature_id, "contains"), *(_edge(feature_id, params[n], "derived_from") for n in uses)]
        edges += [_edge(feature_id, s, "derived_from") for s in known.sources(feature.provenance.ref)]
    return nodes, edges


def _part_node(part_id: str, model_id: str, design: Design, index: int, shape: ShapeDescriptor | None) -> GraphNode:
    part = design.parts[index]
    props: dict[str, Any] = {"title": design.title, "material": part.material}
    if shape is not None:
        props["descriptor"] = shape.model_dump(mode="json")
    return GraphNode(id=part_id, type="part", name=part.name, model_id=model_id, props=props)


def _edge(src: str, dst: str, type_: EdgeType) -> GraphEdge:
    return GraphEdge(src=src, dst=dst, type=type_)


def _by_value(pool: Sequence[Fact], param: Param) -> list[str]:
    return [f.id for f in pool if _matches(f, param)]


def _matches(fact: Fact, param: Param) -> bool:
    if isinstance(fact.value, float) and fact.unit == param.unit and abs(fact.value - param.value) < 1e-6:
        return True
    return fact.count is not None and param.unit == "" and fact.count == param.value


def _mentions(text: str, name: str) -> bool:
    return re.search(rf"(?<![\w.]){re.escape(name)}(?![\w.])", text) is not None


def _names(value: Any) -> set[str]:
    return {name for text in _strings(value) for name in re.findall(r"[a-z][a-z0-9_]*", text)}


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list | tuple):
        for v in value:
            yield from _strings(v)


def _design_text(design: Design, index: int) -> str:
    part = design.parts[index]
    features = " ".join(f"{f.name} {f.intent}" for f in part.features)
    params = " ".join(f"{p.description} {p.provenance.quote or ''}" for p in design.params)
    return f"{design.title} {part.name} {part.material or ''} {features} {params}"
