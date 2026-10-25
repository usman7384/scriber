from collections.abc import Sequence

from partwright_context.models import Chunk
from partwright_context.parsed import Line


def chunk(doc_id: str, lines: Sequence[Line], max_chars: int = 1200) -> list[Chunk]:
    groups: list[list[Line]] = []
    for line in lines:
        text = line.text.strip()
        if not text:
            continue
        current = groups[-1] if groups else []
        size = sum(len(x.text) + 1 for x in current)
        if not current or current[0].page != line.page or text.startswith("#") or size + len(text) > max_chars:
            groups.append([line])
        else:
            current.append(line)
    return [
        Chunk(
            id=f"{doc_id}:c{i}",
            doc_id=doc_id,
            page=g[0].page,
            line_start=g[0].number,
            line_end=g[-1].number,
            text="\n".join(x.text.strip() for x in g),
        )
        for i, g in enumerate(groups, 1)
    ]


def chunk_of(chunks: Sequence[Chunk], page: int, line: int) -> Chunk | None:
    return next((c for c in chunks if c.page == page and c.line_start <= line <= c.line_end), None)
