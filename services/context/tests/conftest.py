from collections.abc import Callable, Iterator
from pathlib import Path

import docx
import openpyxl
import pytest

from scriber_context import HashEmbedder, LocalContext
from scriber_ir import ShapeDescriptor

FIXTURES = Path(__file__).parent / "fixtures"
HOLES = [(f"H{i + 1}", 20 + 40 * (i % 5), 15 if i < 5 else 105, 6.6) for i in range(10)]
BRACKET = ShapeDescriptor(
    bbox_sorted=(5, 60, 80), volume=22000, area=11000, hole_diameters=[6.6] * 4, face_kinds={"plane": 6, "cylinder": 4}
)


def describe(path: Path) -> ShapeDescriptor:
    return BRACKET


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def shape() -> ShapeDescriptor:
    return BRACKET


@pytest.fixture
def ctx(tmp_path: Path) -> Iterator[LocalContext]:
    with LocalContext(tmp_path / "data", HashEmbedder(), describe=describe) as context:
        yield context


@pytest.fixture
def write_pdf(tmp_path: Path) -> Callable[[str, list[list[str]], list[list[str]] | None], Path]:
    def write(name: str, pages: list[list[str]], table: list[list[str]] | None = None) -> Path:
        path = tmp_path / name
        path.write_bytes(_pdf(pages, table))
        return path

    return write


@pytest.fixture
def holes_xlsx(tmp_path: Path) -> Path:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["id", "x (mm)", "y (mm)", "d (mm)"])
    for row in HOLES:
        sheet.append(list(row))
    path = tmp_path / "holes.xlsx"
    book.save(path)
    return path


@pytest.fixture
def spec_docx(tmp_path: Path) -> Path:
    document = docx.Document()
    document.add_paragraph("Bracket specification")
    document.add_paragraph("Material: S355 steel")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text, table.cell(0, 1).text = "thickness", "6 mm"
    table.cell(1, 0).text, table.cell(1, 1).text = "bore", "Ø40 ±0.1 mm"
    document.add_paragraph("Minimum wall thickness 3 mm for milling.")
    path = tmp_path / "spec.docx"
    document.save(str(path))
    return path


def _pdf(pages: list[list[str]], table: list[list[str]] | None) -> bytes:
    contents = [_page_stream(lines, table if i == 0 else None) for i, lines in enumerate(pages)]
    count = len(pages)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(count))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {count} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for i, stream in enumerate(contents):
        page = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>"
        objects += [page.encode(), b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def _page_stream(lines: list[str], table: list[list[str]] | None) -> bytes:
    text = b"BT /F1 11 Tf 14 TL 50 800 Td " + b" ".join(b"(%s) Tj T*" % _escape(line) for line in lines) + b" ET"
    return text + (_table(table) if table else b"")


def _table(rows: list[list[str]], left: int = 50, top: int = 500, width: int = 90, height: int = 18) -> bytes:
    right, bottom = left + width * len(rows[0]), top - height * len(rows)
    grid = [f"{left} {top - i * height} m {right} {top - i * height} l S" for i in range(len(rows) + 1)]
    grid += [f"{left + j * width} {top} m {left + j * width} {bottom} l S" for j in range(len(rows[0]) + 1)]
    cells = [
        b"BT /F1 10 Tf %d %d Td (%s) Tj ET" % (left + j * width + 4, top - i * height - 13, _escape(cell))
        for i, row in enumerate(rows)
        for j, cell in enumerate(row)
    ]
    return b"\n" + "\n".join(grid).encode() + b"\n" + b"\n".join(cells)


def _escape(text: str) -> bytes:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("cp1252")
