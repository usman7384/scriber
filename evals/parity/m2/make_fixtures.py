import csv
from pathlib import Path

import openpyxl

HERE = Path(__file__).parent
REQUIREMENTS = ["Sensor housing requirements", "REQ-1: mount 4×M6", "REQ-2: bore Ø82 ±0.2 mm", "REQ-3: plate 150 × 150 × 8 mm"]  # noqa: RUF001


def pdf(pages: list[list[str]]) -> bytes:
    streams = [b"BT /F1 11 Tf 14 TL 50 800 Td " + b" ".join(b"(%s) Tj T*" % _escape(t) for t in lines) + b" ET" for lines in pages]
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(len(pages)))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for i, stream in enumerate(streams):
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


def _escape(text: str) -> bytes:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("cp1252")


def xlsx(rows: list[list[str]], path: Path) -> None:
    book = openpyxl.Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(rows[0])
    for row in rows[1:]:
        sheet.append([row[0], *(float(v) for v in row[1:])])
    book.save(path)


def main() -> None:
    (HERE / "requirements.pdf").write_bytes(pdf([REQUIREMENTS]))
    (HERE / "requirements-v2.pdf").write_bytes(pdf([[*REQUIREMENTS[:3], "REQ-3: plate 160 × 150 × 8 mm"]]))  # noqa: RUF001
    (HERE / "report.pdf").write_bytes(
        pdf([["Enclosure sizing report", "Load case 1: 40 N on the lid"], ["Computed wall thickness 3.2 mm"]])
    )
    with (HERE / "holes.csv").open(encoding="utf-8") as f:
        xlsx(list(csv.reader(f)), HERE / "holes.xlsx")


if __name__ == "__main__":
    main()
