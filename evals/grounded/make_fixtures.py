import csv
import shutil
import sys
from pathlib import Path

import docx
import openpyxl

from partwright_geometry import LocalGeometry
from partwright_ir import Design

ROOT = Path(__file__).parent / "files"


def pdf(path: Path, lines: list[str]) -> None:
    def esc(t: str) -> bytes:
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("cp1252")

    stream = b"BT /F1 11 Tf 14 TL 50 800 Td " + b" ".join(b"(%s) Tj T*" % esc(line) for line in lines) + b" ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    path.write_bytes(bytes(out))


def text(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def word(path: Path, lines: list[str]) -> None:
    d = docx.Document()
    for line in lines:
        d.add_paragraph(line)
    d.save(str(path))


def plate_design(length: float, width: float, thickness: float, spacing: tuple[float, float]) -> Design:
    holes = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": spacing[0], "spacing_y": spacing[1]}
    return Design.model_validate(
        {
            "title": "Previous plate",
            "params": [
                {"name": "length", "value": length, "unit": "mm"},
                {"name": "width", "value": width, "unit": "mm"},
                {"name": "thickness", "value": thickness, "unit": "mm"},
            ],
            "parts": [
                {
                    "id": "plate",
                    "name": "Plate",
                    "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "length", "height": "width"}]}],
                    "features": [
                        {"kind": "extrude", "id": "body", "name": "Plate", "sketch": "s", "distance": "thickness"},
                        {"kind": "hole", "id": "mount", "name": "Mounting holes", "at": holes, "diameter": 6.6},
                    ],
                }
            ],
        }
    )


def step(geometry: LocalGeometry, path: Path, design: Design) -> None:
    work = path.parent / "_build"
    art = geometry.build(design, work)
    shutil.copyfile(art.files["step"], path)
    shutil.rmtree(work)


def main(root: Path) -> None:
    def case(name: str) -> Path:
        (root / name).mkdir(parents=True, exist_ok=True)
        return root / name

    g = LocalGeometry()
    try:
        c = case("g01-sensor-plate")
        pdf(
            c / "requirements.pdf",
            [
                "Sensor mounting plate - requirements",
                "REQ-1 Plate size 120 x 80 x 6 mm",
                "REQ-2 Mounting: 4 x M6 through holes",
                "REQ-3 Sensor bore Ø20 +/- 0.1 mm through, centred",
                "Material: Al 6082",
            ],
        )
        text(
            c / "plate-design-rules.md",
            [
                "# Plate design rules",
                "",
                "- Hole-to-edge distance must be at least 2 x D for all through holes.",
                "- Minimum wall thickness 3 mm.",
            ],
        )
        step(g, c / "previous-sensor-plate.step", plate_design(110, 75, 6, (80, 45)))

        c = case("g02-nema23-docx")
        word(
            c / "motor-plate-spec.docx",
            [
                "Motor plate for a NEMA 23 stepper",
                "Plate: 80 x 80 x 8 mm",
                "Pilot bore Ø38.1 +0.05/-0 mm",
                "Mounting: 4 x M5 holes on a 47.14 mm square",
                "Material: Al 6061",
            ],
        )

        c = case("g03-hole-table-xlsx")
        text(c / "drilled-plate.md", ["# Drilled plate", "", "Plate: 200 x 120 x 5 mm", "Holes as listed in holes.xlsx, all through."])
        wb = openpyxl.Workbook()
        ws = wb.active
        assert ws is not None
        ws.title = "holes"
        ws.append(["id", "x (mm)", "y (mm)", "Ø (mm)"])
        for i, (x, y) in enumerate([(x, y) for y in (15, 105) for x in (20, 60, 100, 140, 180)], 1):
            ws.append([f"H{i}", x, y, 6.6])
        wb.save(str(c / "holes.xlsx"))

        c = case("g04-enclosure-yaml")
        text(c / "enclosure.yaml", ["enclosure:", "  outer_length: 120 mm", "  outer_width: 80 mm", "  outer_height: 40 mm", "  open: top"])
        text(c / "Box_Best_Practice.md", ["# Box best practice", "", "Team conventions for enclosures:", "- Wall thickness: 2.5 mm"])
        text(c / "enclosure-rules.md", ["# Rules", "", "- Minimum wall thickness 2 mm."])

        c = case("g05-flange-pdf")
        pdf(
            c / "flange-spec.pdf",
            [
                "Pipe flange",
                "Outer diameter Ø140 mm",
                "Thickness 12 mm",
                "Bolt holes: 6 x Ø9 on a 110 mm pitch circle",
                "Bore Ø60 +/- 0.1 mm",
                "Standard: EN 1092-1",
            ],
        )
        text(c / "flange-rules.md", ["# Flange rules", "", "- Hole-to-edge distance at least 1.5 x D."])

        c = case("g06-base-plate-txt")
        text(
            c / "base-plate.txt",
            [
                "REQ-1 Base plate 150 x 100 x 10 mm",
                "REQ-2 Corner holes: 4 x Ø11 for M10",
                "REQ-3 Hole centres 15 mm from each edge",
                "REQ-4 Material S355",
            ],
        )

        c = case("g07-spacer-csv")
        with (c / "spacer.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerows([["parameter", "value", "unit"], ["outer diameter", 30, "mm"], ["bore diameter", 12.5, "mm"], ["length", 20, "mm"]])

        c = case("g08-milled-pocket")
        text(
            c / "cover-plate.md",
            [
                "# Cover plate",
                "",
                "Plate: 100 x 60 x 10 mm",
                "Rectangular pocket 60 x 30 mm, 4 mm deep, centred on the top face.",
                "Machined from Al 6082 on a 3-axis mill.",
            ],
        )
        text(c / "milling-rules.md", ["# Milling rules", "", "- Internal corners must have a radius of at least 3 mm for milling."])

        c = case("g09-previous-step")
        step(g, c / "previous-plate.step", plate_design(100, 70, 6, (80, 50)))
        text(c / "new-plate.md", ["# New plate", "", "Same as previous-plate.step but 150 mm long; keep its width, thickness and holes."])

        c = case("g10-fdm-bracket")
        text(c / "printed-plate.md", ["# Printed plate", "", "Plate 70 x 40 x 4 mm with 2 x M4 holes 50 mm apart."])
        text(
            c / "printing-rules.md",
            [
                "# Printing rules",
                "",
                "- Overhangs should not exceed 45 degrees for FDM printing.",
                "- Hole-to-edge distance should be at least 2 x D.",
            ],
        )
    finally:
        g.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT)
