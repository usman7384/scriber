from dataclasses import dataclass

from scriber_ir import ShapeDescriptor

Row = tuple[int, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class Line:
    page: int
    number: int
    text: str


@dataclass(frozen=True, slots=True)
class Table:
    page: int
    rows: tuple[Row, ...]


@dataclass(frozen=True, slots=True)
class Parsed:
    lines: tuple[Line, ...] = ()
    tables: tuple[Table, ...] = ()
    pages: int = 1
    descriptor: ShapeDescriptor | None = None


def row_text(cells: tuple[str, ...]) -> str:
    return f"{cells[0]}: {cells[1]}" if len(cells) == 2 else " | ".join(cells)


def table_lines(table: Table) -> list[Line]:
    return [Line(table.page, number, row_text(cells)) for number, cells in table.rows]
