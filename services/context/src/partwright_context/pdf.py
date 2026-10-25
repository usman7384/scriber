from pathlib import Path
from typing import Any

import pdfplumber
import pypdfium2

from partwright_context.parsed import Line, Parsed, Row, Table


def read_pdf(path: Path) -> Parsed:
    pages = _page_lines(path)
    lines = tuple(line for page in pages for line in page)
    with pdfplumber.open(path) as pdf:
        tables = tuple(
            Table(i, tuple(_rows(raw, pages[i - 1]))) for i, page in enumerate(pdf.pages, 1) for raw in page.extract_tables() if raw
        )
    return Parsed(lines=lines, tables=tables, pages=len(pages))


def _page_lines(path: Path) -> list[list[Line]]:
    pdf = pypdfium2.PdfDocument(path)
    try:
        return [[Line(i, n, text) for n, text in enumerate(_text(page).splitlines(), 1)] for i, page in enumerate(pdf, 1)]
    finally:
        pdf.close()


def _text(page: Any) -> str:
    return str(page.get_textpage().get_text_range())


def _rows(raw: list[list[str | None]], lines: list[Line]) -> list[Row]:
    rows = [tuple((c or "").strip() for c in r) for r in raw]
    return [(_line_of(cells, lines), cells) for cells in rows if any(cells)]


def _line_of(cells: tuple[str, ...], lines: list[Line]) -> int:
    present = [c for c in cells if c]
    return next((line.number for line in lines if all(c in line.text for c in present)), 0)
