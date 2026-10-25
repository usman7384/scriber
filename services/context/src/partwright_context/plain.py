import csv
import re
from pathlib import Path
from xml.parsers import expat

import yaml

from partwright_context.parsed import Line, Parsed, Row, Table, table_lines

SEPARATOR = re.compile(r"^\|?\s*:?-{3,}")


def read_text(path: Path) -> Parsed:
    lines: list[Line] = []
    rows: list[Row] = []
    tables: list[Table] = []
    for number, text in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if text.lstrip().startswith("|"):
            if not SEPARATOR.match(text.strip()):
                rows.append((number, tuple(c.strip() for c in text.strip().strip("|").split("|"))))
            continue
        if rows:
            tables.append(Table(1, tuple(rows)))
            rows = []
        lines.append(Line(1, number, text))
    if rows:
        tables.append(Table(1, tuple(rows)))
    table_rows = [line for t in tables for line in table_lines(t)]
    return Parsed(lines=tuple(sorted([*lines, *table_rows], key=lambda line: line.number)), tables=tuple(tables))


def read_csv(path: Path) -> Parsed:
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = tuple((n, tuple(c.strip() for c in cells)) for n, cells in enumerate(csv.reader(text.splitlines(), dialect), 1) if any(cells))
    table = Table(1, rows)
    return Parsed(lines=tuple(table_lines(table)), tables=(table,))


def read_yaml(path: Path) -> Parsed:
    root = yaml.compose(path.read_text(encoding="utf-8-sig"))
    return Parsed(lines=tuple(_yaml_lines(root, ""))) if root is not None else Parsed()


def _yaml_lines(node: yaml.Node, prefix: str) -> list[Line]:
    if isinstance(node, yaml.MappingNode):
        return [line for key, value in node.value for line in _yaml_lines(value, _join(prefix, str(key.value)))]
    if isinstance(node, yaml.SequenceNode):
        return [line for i, item in enumerate(node.value) for line in _yaml_lines(item, _join(prefix, str(i)))]
    return [Line(1, node.start_mark.line + 1, f"{prefix}: {node.value}" if prefix else str(node.value))]


def read_xml(path: Path) -> Parsed:
    parser = expat.ParserCreate()
    stack: list[tuple[str, int, list[str]]] = []
    lines: list[Line] = []

    def start(tag: str, attrs: dict[str, str]) -> None:
        path_ = _join(stack[-1][0] if stack else "", tag)
        stack.append((path_, parser.CurrentLineNumber, []))
        lines.extend(Line(1, parser.CurrentLineNumber, f"{path_}.{k}: {v}") for k, v in attrs.items())

    def end(_tag: str) -> None:
        path_, number, text = stack.pop()
        if "".join(text).strip():
            lines.append(Line(1, number, f"{path_}: {' '.join(''.join(text).split())}"))

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = lambda data: stack[-1][2].append(data)
    parser.Parse(path.read_bytes(), True)
    return Parsed(lines=tuple(sorted(lines, key=lambda line: line.number)))


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key
