import re

from scriber_context.models import Fact
from scriber_context.parsed import Table, row_text
from scriber_context.quantities import MINUS, NUM, PINT, normalise, number
from scriber_ir import Provenance

DIAMETERS = {"d", "dia", "diam", "diameter", "ø", "⌀", "hole diameter", "hole dia", "hole ø"}
IDS = {"id", "hole", "#", "name", "no", "nr"}


def hole_facts(doc_id: str, table: Table) -> list[Fact]:
    for i, (_, cells) in enumerate(table.rows):
        columns = _columns(cells)
        if {"x", "y", "d"} <= columns.keys():
            return [f for n, (line, row) in enumerate(table.rows[i + 1 :], 1) if (f := _hole(doc_id, table.page, line, row, columns, n))]
    return []


def _columns(cells: tuple[str, ...]) -> dict[str, tuple[int, str]]:
    out: dict[str, tuple[int, str]] = {}
    for i, cell in enumerate(cells):
        unit = re.search(r"[(\[]\s*([^)\]]+?)\s*[)\]]", cell)
        name = re.sub(r"[(\[].*?[)\]]", "", cell).strip().lower().replace("_", " ")
        role = "d" if name in DIAMETERS else "id" if name in IDS else name
        if role in {"x", "y", "d", "id"} and role not in out:
            out[role] = (i, unit[1] if unit and unit[1] in PINT else "mm")
    return out


def _hole(doc_id: str, page: int, line: int, row: tuple[str, ...], columns: dict[str, tuple[int, str]], n: int) -> Fact | None:
    values = {role: row[i].replace(MINUS, "-") if i < len(row) else "" for role, (i, _) in columns.items()}
    if not all(re.fullmatch(rf"-?{NUM}", values[r]) for r in ("x", "y", "d")):
        return None
    x, y, d = (normalise(number(values[r]), columns[r][1])[0] for r in ("x", "y", "d"))
    label = values.get("id") or str(n)
    return Fact(
        id=f"{doc_id}:{page}.{line}.h{n}",
        doc_id=doc_id,
        kind="hole",
        name=f"hole_{label}".lower(),
        value=d,
        unit="mm",
        at=(x, y),
        page=page,
        line=line,
        text=row_text(row),
        source=Provenance(source="document", ref=f"{doc_id}#p{page}:l{line}", quote=row_text(row)[:160]),
    )
