from collections.abc import Callable
from pathlib import Path

import pytest

from scriber_context.readers import kind_of, read
from scriber_context.tables import hole_facts
from scriber_ir import ShapeDescriptor

WritePdf = Callable[[str, list[list[str]], list[list[str]] | None], Path]


def texts(path: Path) -> list[tuple[int, int, str]]:
    return [(x.page, x.number, x.text) for x in read(path, kind_of(path), None).lines if x.text.strip()]


def test_pdf_text_keeps_pages_and_lines_and_tables_come_from_pdfplumber(write_pdf: WritePdf) -> None:
    path = write_pdf("req.pdf", [["Requirements", "REQ-2: bore Ø82 ±0.2 mm"], ["Second page"]], [["x", "y", "d"], ["10", "20", "6.6"]])
    parsed = read(path, "pdf", None)
    assert parsed.pages == 2
    assert (1, 2, "REQ-2: bore Ø82 ±0.2 mm") in [(x.page, x.number, x.text) for x in parsed.lines]
    assert (2, 1, "Second page") in [(x.page, x.number, x.text) for x in parsed.lines]
    [table] = parsed.tables
    assert [cells for _, cells in table.rows] == [("x", "y", "d"), ("10", "20", "6.6")]
    [hole] = hole_facts("d0", table)
    assert (hole.value, hole.at, hole.page) == (6.6, (10.0, 20.0), 1)


def test_docx_paragraphs_and_tables_in_document_order(spec_docx: Path) -> None:
    assert texts(spec_docx) == [
        (1, 1, "Bracket specification"),
        (1, 2, "Material: S355 steel"),
        (1, 3, "thickness: 6 mm"),
        (1, 4, "bore: Ø40 ±0.1 mm"),
        (1, 5, "Minimum wall thickness 3 mm for milling."),
    ]


def test_markdown_tables_become_rows_and_key_value_lines(fixtures: Path) -> None:
    parsed = read(fixtures / "plate_spec.md", "md", None)
    [table] = parsed.tables
    assert table.rows[0] == (7, ("id", "x (mm)", "y (mm)", "Ø (mm)"))
    assert len(table.rows) == 11
    assert 8 not in [x.number for x in parsed.lines]


def test_xml_lines_carry_element_paths_and_source_lines(fixtures: Path) -> None:
    assert texts(fixtures / "sizing.xml") == [
        (1, 2, "aircraft.name: UAV-1"),
        (1, 4, "aircraft.wing.span.unit: mm"),
        (1, 4, "aircraft.wing.span: 1200"),
        (1, 5, "aircraft.wing.chord: 180 mm"),
    ]


def test_yaml_lines_are_flattened_with_source_lines(fixtures: Path) -> None:
    assert texts(fixtures / "enclosure.yaml") == [
        (1, 2, "enclosure.wall: 2.5 mm"),
        (1, 4, "enclosure.bosses.count: 4"),
        (1, 5, "enclosure.bosses.thread: M3"),
    ]


def test_spreadsheet_sheets_are_pages(holes_xlsx: Path) -> None:
    parsed = read(holes_xlsx, "xlsx", None)
    assert parsed.pages == 1
    assert parsed.tables[0].rows[1] == (2, ("H1", "20", "15", "6.6"))


def test_images_have_no_text(tmp_path: Path) -> None:
    path = tmp_path / "photo.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert read(path, kind_of(path), None).lines == ()


def test_cad_files_use_the_injected_describer(fixtures: Path, shape: ShapeDescriptor) -> None:
    parsed = read(fixtures / "bracket.step", "step", lambda _path: shape)
    assert parsed.descriptor == shape
    assert parsed.lines[0].text == "bracket STEP part: bounding box 5 x 60 x 80 mm, volume 22000 mm3, holes Ø6.6"


def test_cad_without_describer_and_unknown_types_fail(fixtures: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="shape describer"):
        read(fixtures / "bracket.step", "step", None)
    with pytest.raises(ValueError, match="unsupported"):
        kind_of(tmp_path / "model.sldprt")
