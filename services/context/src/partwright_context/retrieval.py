from collections.abc import Mapping, Sequence

from partwright_context.embed import cosine
from partwright_context.models import GraphNode, PartRef
from partwright_context.shapes import similarity
from partwright_ir import Design, ShapeDescriptor


def fuse(rankings: Sequence[Sequence[str]], c: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking):
            scores[item] = scores.get(item, 0.0) + 1 / (c + rank + 1)
    return sorted(scores, key=lambda i: (-scores[i], i))


def similar_parts(
    parts: Sequence[GraphNode],
    vectors: Mapping[str, list[float]],
    designs: Mapping[str, Design],
    query: list[float],
    shape: ShapeDescriptor | None,
    k: int,
) -> list[PartRef]:
    refs = []
    for node in parts:
        raw = node.props.get("descriptor")
        descriptor = ShapeDescriptor.model_validate(raw) if raw else None
        text = max(0.0, cosine(query, vectors[node.id])) if node.id in vectors else 0.0
        geometric = similarity(shape, descriptor) if shape and descriptor else 0.0
        refs.append(
            PartRef(
                id=node.id,
                name=node.name,
                origin="generated" if node.model_id else "uploaded",
                model_id=node.model_id,
                doc_id=node.doc_id,
                descriptor=descriptor,
                design=designs.get(node.model_id) if node.model_id else None,
                score=round(text if shape is None else (text + geometric) / 2, 6),
            )
        )
    return sorted((r for r in refs if r.score > 0), key=lambda r: (-r.score, r.id))[:k]
