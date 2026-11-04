from pathlib import Path
from typing import Any

import docx
import openpyxl
from docx.table import Table as DocxTable

from scriber_context.parsed import Line, Parsed, Row, Table, table_lines


def read_docx(path: Path) -> Parsed:
    lines: list[Line] = []
    tables: list[Table] = []
    number = 0
    for block in docx.Document(str(path)).iter_inner_content():
        if isinstance(block, DocxTable):
            rows: list[Row] = []
            for row in block.rows:
                number += 1
                rows.append((number, tuple(cell.text.strip() for cell in row.cells)))
            table = Table(1, tuple(rows))
            tables.append(table)
            lines.extend(table_lines(table))
        else:
            number += 1
            lines.append(Line(1, number, block.text))
    return Parsed(lines=tuple(lines), tables=tuple(tables))


def read_xlsx(path: Path) -> Parsed:
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        tables = [_sheet(page, sheet) for page, sheet in enumerate(book.worksheets, 1)]
    finally:
        book.close()
    return Parsed(lines=tuple(line for t in tables for line in table_lines(t)), tables=tuple(tables), pages=len(tables))


def _sheet(page: int, sheet: Any) -> Table:
    rows: list[Row] = []
    for number, values in enumerate(sheet.iter_rows(values_only=True), 1):
        cells = tuple("" if v is None else _cell(v) for v in values)
        if any(cells):
            rows.append((number, cells))
    return Table(page, tuple(rows))


def _cell(value: object) -> str:
    return f"{value:g}" if isinstance(value, float) else str(value).strip()
