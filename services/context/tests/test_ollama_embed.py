import os
from pathlib import Path

import pytest

from partwright_context import LocalContext, OllamaEmbedder

MODEL = os.environ.get("PARTWRIGHT_EMBED_MODEL", "qwen3-embedding:0.6b")


@pytest.mark.llm
def test_ollama_embeddings_drive_retrieval(tmp_path: Path, fixtures: Path) -> None:
    embedder = OllamaEmbedder(MODEL)
    [vector] = embedder.embed(["minimum wall thickness"])
    assert len(vector) == embedder.dim
    with LocalContext(tmp_path, embedder) as ctx:
        rules = ctx.ingest("p1", fixtures / "screw-design-norm.md")
        ctx.ingest("p1", fixtures / "kmm_notes.txt")
        pack = ctx.retrieve("p1", "how far must holes stay from the edge", k=1)
    assert pack.chunks[0].doc_id == rules.id
    assert "min_hole_edge_ratio" in [r.id for r in pack.rules]
