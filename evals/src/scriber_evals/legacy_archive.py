import argparse
import random
import shutil
from pathlib import Path

from scriber_geometry import LocalGeometry
from scriber_ir import Design

STEPS, PDFS = 50, 20
# one damaged file of each kind, so the report has failures to show
BROKEN_STEP, BROKEN_PDF = "part-049.step", "spec-019.pdf"


def make_archive(folder: Path, geometry: LocalGeometry, seed: int = 0) -> list[Path]:
    rng = random.Random(seed)
    (folder / "cad").mkdir(parents=True, exist_ok=True)
    (folder / "docs").mkdir(parents=True, exist_ok=True)
    steps = [_step(folder / "cad" / f"part-{i:03d}.step", geometry, *_dims(rng)) for i in range(STEPS)]
    pdfs = [_pdf_file(folder / "docs" / f"spec-{i:03d}.pdf", i, *_dims(rng)) for i in range(PDFS)]
    (folder / "cad" / BROKEN_STEP).write_bytes((folder / "cad" / BROKEN_STEP).read_bytes()[:400])
    (folder / "docs" / BROKEN_PDF).write_bytes(b"%PDF-1.4\n%damaged in transfer\n")
    return steps + pdfs


def _dims(rng: random.Random) -> tuple[int, int, int, float]:
    return rng.randrange(40, 200), rng.randrange(30, 120), rng.randrange(3, 12), rng.choice([3.4, 4.5, 5.5, 6.6, 9.0])


def _step(path: Path, geometry: LocalGeometry, length: int, width: int, thickness: int, hole: float) -> Path:
    design = Design.model_validate(
        {
            "title": path.stem,
            "params": [{"name": n, "value": v, "unit": "mm"} for n, v in (("l", length), ("w", width), ("t", thickness), ("d", hole))],
            "parts": [
                {
                    "id": "plate",
                    "name": path.stem,
                    "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "l", "height": "w"}]}],
                    "features": [
                        {"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": "t"},
                        {
                            "kind": "hole",
                            "id": "holes",
                            "name": "Holes",
                            "plane": {"offset": "t"},
                            "at": {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": "l / 2", "spacing_y": "w / 2"},
                            "diameter": "d",
                        },
                    ],
                }
            ],
        }
    )
    art = geometry.build(design, path.parent / f".build-{path.stem}")
    shutil.copyfile(art.files["step"], path)
    shutil.rmtree(art.files["step"].parent)
    return path


def _pdf_file(path: Path, i: int, length: int, width: int, thickness: int, hole: float) -> Path:
    lines = [f"Drawing note D-{i:03d}", f"Plate {length} x {width} x {thickness} mm", f"4 holes diameter {hole} mm", "Material 6061-T6"]
    path.write_bytes(pdf(lines))
    return path


def pdf(lines: list[str]) -> bytes:
    text = " ".join(f"({line}) Tj T*" for line in lines)
    stream = f"BT /F1 11 Tf 14 TL 50 800 Td {text} ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
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
    return bytes(out)


def main() -> None:
    p = argparse.ArgumentParser(description="Write the CX-12 legacy archive: 50 STEP and 20 PDF files, one of each damaged")
    p.add_argument("out", type=Path)
    args = p.parse_args()
    geometry = LocalGeometry()
    try:
        print(f"{len(make_archive(args.out, geometry))} files in {args.out}")
    finally:
        geometry.close()


if __name__ == "__main__":
    main()
