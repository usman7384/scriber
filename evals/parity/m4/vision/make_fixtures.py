import json
import math
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
INK = (55, 55, 70)
Point = tuple[float, float]


def oblique(origin: Point, scale: float, x: float, y: float, z: float) -> Point:
    return origin[0] + scale * (x + 0.45 * y), origin[1] - scale * (z + 0.3 * y)


def pencil(draw: ImageDraw.ImageDraw, a: Point, b: Point, rng: random.Random) -> None:
    mid = ((a[0] + b[0]) / 2 + rng.uniform(-2, 2), (a[1] + b[1]) / 2 + rng.uniform(-2, 2))
    draw.line([a, mid, b], fill=INK, width=3, joint="curve")


def sketch() -> Image.Image:
    rng, image = random.Random(4), Image.new("RGB", (900, 620), (250, 248, 240))
    draw, font = ImageDraw.Draw(image), ImageFont.load_default(size=30)

    def p(x: float, y: float, z: float) -> Point:
        return oblique((150, 470), 5, x, y, z)

    profile = [(0, 0), (120, 0), (120, 4), (4, 4), (4, 30), (0, 30)]
    for y in (0, 40):
        for (x0, z0), (x1, z1) in zip(profile, profile[1:] + profile[:1], strict=True):
            pencil(draw, p(x0, y, z0), p(x1, y, z1), rng)
    for x, z in profile:
        pencil(draw, p(x, 0, z), p(x, 40, z), rng)
    for x in (40, 90):
        cx, cy = p(x, 20, 4)
        draw.ellipse([cx - 15, cy - 7, cx + 15, cy + 7], outline=INK, width=3)
    pencil(draw, p(0, 0, -9), p(120, 0, -9), rng)
    draw.text(p(52, 0, -12), "120", fill=INK, font=font)
    pencil(draw, p(126, 0, 0), p(126, 40, 0), rng)
    draw.text(p(130, 24, 0), "40", fill=INK, font=font)
    pencil(draw, p(120, 0, 2), p(127, 0, -8), rng)
    draw.text(p(128, 0, -6), "4", fill=INK, font=font)
    pencil(draw, p(90, 20, 4), p(105, 20, 34), rng)
    diameter_label(draw, p(106, 20, 36), "2x", "6", font)
    return image


def diameter_label(draw: ImageDraw.ImageDraw, at: Point, count: str, size: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> None:
    # the bundled font has no diameter sign, so it is drawn as a hand-written circle and slash
    x, y = at[0] + draw.textlength(count + " ", font=font), at[1] + 8
    draw.text(at, count, fill=INK, font=font)
    draw.ellipse([x, y, x + 20, y + 20], outline=INK, width=3)
    draw.line([(x - 3, y + 24), (x + 23, y - 4)], fill=INK, width=3)
    draw.text((x + 26, at[1]), size, fill=INK, font=font)


def shade(rgb: tuple[int, int, int], k: float) -> tuple[int, int, int]:
    r, g, b = (min(255, int(c * k)) for c in rgb)
    return r, g, b


def box(draw: ImageDraw.ImageDraw, lo: tuple[float, float, float], hi: tuple[float, float, float], rgb: tuple[int, int, int]) -> None:
    def p(x: float, y: float, z: float) -> Point:
        return oblique((170, 520), 14, x, y, z)

    (x0, y0, z0), (x1, y1, z1) = lo, hi
    faces = [
        ([p(x0, y0, z0), p(x1, y0, z0), p(x1, y0, z1), p(x0, y0, z1)], 1.0),
        ([p(x0, y0, z1), p(x1, y0, z1), p(x1, y1, z1), p(x0, y1, z1)], 1.35),
        ([p(x1, y0, z0), p(x1, y1, z0), p(x1, y1, z1), p(x1, y0, z1)], 0.7),
    ]
    for corners, k in faces:
        draw.polygon(corners, fill=shade(rgb, k), outline=(20, 20, 30))


def servo() -> Image.Image:
    image = Image.new("RGB", (800, 640), (236, 238, 242))
    draw, blue = ImageDraw.Draw(image), (40, 70, 160)

    def p(x: float, y: float, z: float) -> Point:
        return oblique((170, 520), 14, x, y, z)

    box(draw, (-5, 0, 15.9), (0, 11.8, 18.4), blue)
    box(draw, (0, 0, 0), (22.2, 11.8, 22.7), blue)
    box(draw, (22.2, 0, 15.9), (27.2, 11.8, 18.4), blue)
    for x in (-2.8, 25.0):
        cx, cy = p(x, 5.9, 18.4)
        draw.ellipse([cx - 14, cy - 6, cx + 14, cy + 6], fill=(30, 30, 40))
    cx, cy = p(5.9, 5.9, 22.7)
    top = cy - 4 * 14
    draw.rectangle([cx - 34, top, cx + 34, cy], fill=(235, 235, 235), outline=(90, 90, 90))
    draw.ellipse([cx - 34, top - 12, cx + 34, top + 12], fill=(250, 250, 250), outline=(90, 90, 90))
    for k, colour in enumerate(((120, 70, 30), (200, 40, 40), (240, 150, 30))):
        a = p(0, 3 + 2.5 * k, 3)
        draw.line([a, (a[0] - 90, a[1] + 40 + 6 * k), (a[0] - 150, a[1] + 90 + 6 * k)], fill=colour, width=7)
    return image


class Pdf:
    def __init__(self) -> None:
        self.ops: list[str] = []

    def line(self, *points: Point, width: float = 1.0, dash: str = "[] 0") -> None:
        path = " ".join(f"{x:.2f} {y:.2f} {'m' if i == 0 else 'l'}" for i, (x, y) in enumerate(points))
        self.ops.append(f"{width} w {dash} d {path} S")

    def circle(self, c: Point, r: float, width: float = 1.0, dash: str = "[] 0") -> None:
        k, (x, y) = 0.5523 * r, c
        arcs = (
            f"{x + r} {y} m {x + r} {y + k} {x + k} {y + r} {x} {y + r} c {x - k} {y + r} {x - r} {y + k} {x - r} {y} c "
            f"{x - r} {y - k} {x - k} {y - r} {x} {y - r} c {x + k} {y - r} {x + r} {y - k} {x + r} {y} c"
        )
        self.ops.append(f"{width} w {dash} d {arcs} S")

    def text(self, at: Point, s: str, size: int = 11) -> None:
        escaped = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        self.ops.append(f"BT /F1 {size} Tf {at[0]:.2f} {at[1]:.2f} Td ({escaped}) Tj ET")

    def bytes(self) -> bytes:
        stream = "\n".join(self.ops).encode("cp1252")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [4 0 R] /Count 1 >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        ]
        out, offsets = bytearray(b"%PDF-1.4\n"), []
        for n, body in enumerate(objects, 1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offsets)
        out += b"trailer << /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
        return bytes(out)


def flange_drawing() -> bytes:
    pdf, s, c = Pdf(), 2.0, (230.0, 300.0)
    centre = "[12 3 2 3] 0"
    pdf.circle(c, 60 * s, 1.6)
    pdf.circle(c, 45 * s, 0.6, centre)
    pdf.circle(c, 30 * s, 1.2)
    pdf.circle(c, 15 * s, 1.2)
    for i in range(6):
        a = math.radians(90 + 60 * i)
        pdf.circle((c[0] + 45 * s * math.cos(a), c[1] + 45 * s * math.sin(a)), 5.5 * s, 1.2)
    pdf.line((c[0] - 135, c[1]), (c[0] + 135, c[1]), width=0.5, dash=centre)
    pdf.line((c[0], c[1] - 135), (c[0], c[1] + 135), width=0.5, dash=centre)
    pdf.line((c[0] - 60 * s, c[1] - 150), (c[0] + 60 * s, c[1] - 150), width=0.6)
    pdf.text((c[0] - 18, c[1] - 165), "Ø120")
    pdf.line((c[0] + 32, c[1] + 78), (c[0] + 110, c[1] + 160), width=0.6)
    pdf.text((c[0] + 112, c[1] + 162), "PCD Ø90")
    pdf.line((c[0] + 45 * s * math.cos(math.radians(30)), c[1] + 45 * s * 0.5), (c[0] + 150, c[1] + 120), width=0.6)
    pdf.text((c[0] + 152, c[1] + 122), "6\N{MULTIPLICATION SIGN} Ø11 THRU EQ SP")
    pdf.line((c[0] - 30 * s * 0.7, c[1] - 30 * s * 0.7), (c[0] - 120, c[1] - 120), width=0.6)
    pdf.text((c[0] - 175, c[1] - 132), "HUB Ø60")
    pdf.line((c[0] + 15 * s * 0.7, c[1] - 15 * s * 0.7), (c[0] + 120, c[1] - 110), width=0.6)
    pdf.text((c[0] + 122, c[1] - 116), "BORE Ø30")
    x0, y0 = 560.0, 180.0

    def at(z: float, y: float) -> Point:
        return x0 + z * s, y0 + y * s

    pdf.line(at(0, 0), at(12, 0), at(12, 30), at(32, 30), at(32, 90), at(12, 90), at(12, 120), at(0, 120), at(0, 0), width=1.6)
    for y in (45, 75):
        pdf.line(at(0, y), at(32, y), width=0.6, dash="[4 3] 0")
    pdf.line((x0 - 10, y0 + 60 * s), (x0 + 80, y0 + 60 * s), width=0.5, dash=centre)
    pdf.line((x0, y0 - 25), (x0 + 12 * s, y0 - 25), width=0.6)
    pdf.text((x0 + 2, y0 - 40), "12")
    pdf.line((x0, y0 - 55), (x0 + 32 * s, y0 - 55), width=0.6)
    pdf.text((x0 + 22, y0 - 70), "32")
    pdf.text((x0 - 20, y0 + 270), "SECTION A-A")
    pdf.text((60, 40), "FLANGE   material S235   units mm   all holes through", 10)
    return pdf.bytes()


def plate(length: float, width: float) -> list[dict[str, Any]]:
    return [{"id": "s", "entities": [{"kind": "rect", "width": length, "height": width}]}]


def holes(hid: str, plane: dict[str, Any], points: list[list[float]], diameter: float) -> dict[str, Any]:
    at = {"kind": "points", "points": points}
    return {"kind": "hole", "id": hid, "name": "Holes", "plane": plane, "at": at, "diameter": diameter}


def part(sketches: list[dict[str, Any]], features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"title": "Part", "params": [], "parts": [{"id": "part", "name": "Part", "sketches": sketches, "features": features}]}


def extrude(sketch: str, distance: float, **extra: Any) -> dict[str, Any]:
    return {"kind": "extrude", "id": f"{sketch}_body", "name": "Body", "sketch": sketch, "distance": distance, **extra}


def polar(count: int, pcd: float) -> list[list[float]]:
    angles = [2 * math.pi * i / count for i in range(count)]
    return [[round(pcd / 2 * math.cos(a), 3), round(pcd / 2 * math.sin(a), 3)] for a in angles]


def critic_cases() -> list[dict[str, Any]]:
    top5, top6 = {"offset": 5}, {"offset": 6}
    disc = [{"id": "s", "entities": [{"kind": "circle", "diameter": 100}]}]
    motor = [{"id": "s", "entities": [{"kind": "rect", "width": 60, "height": 60}, {"kind": "circle", "diameter": 22, "subtract": True}]}]
    outline = [[0, 0], [60, 0], [60, 5], [5, 5], [5, 40], [0, 40]]
    profile = [{"id": "s", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": outline}]}]
    return [
        {
            "request": "Mounting plate 80 x 60 x 5 mm with four 6.6 mm holes, one near each corner.",
            "design": part(plate(80, 60), [extrude("s", 5), holes("h", top5, [[-30, -20], [30, -20], [-30, 20], [30, 20]], 6.6)]),
        },
        {
            "request": "Round flange plate, 100 mm diameter, 8 mm thick, six 9 mm bolt holes evenly spaced on an 80 mm circle.",
            "design": part(disc, [extrude("s", 8), holes("h", {"offset": 8}, polar(6, 80), 9)]),
        },
        {
            "request": "Flat bar 120 x 20 x 6 mm with three 8 mm holes in a row along its length, 45 mm apart.",
            "design": part(plate(120, 20), [extrude("s", 6), holes("h", top6, [[-45, 0], [0, 0], [45, 0]], 8)]),
        },
        {
            "request": "L-bracket, 5 mm thick, 30 mm wide, base leg 60 mm, upright leg 40 mm, two 6.5 mm holes side by side in the base.",
            "design": part(profile, [extrude("s", 30, extent="symmetric"), holes("h", {"offset": 0}, [[35, -8], [35, 8]], 6.5)]),
        },
        {
            "request": "NEMA 17 motor plate 60 x 60 x 6 mm with a 22 mm centre bore and four 3.4 mm screw holes on a 31 mm square.",
            "design": part(motor, [extrude("s", 6), holes("h", top6, [[-15.5, -15.5], [15.5, -15.5], [-15.5, 15.5], [15.5, 15.5]], 3.4)]),
        },
    ]


def main() -> None:
    sketch().save(HERE / "l_bracket_sketch.png", optimize=True)
    servo().save(HERE / "servo.png", optimize=True)
    (HERE / "flange_drawing.pdf").write_bytes(flange_drawing())
    (HERE / "critic_cases.json").write_text(json.dumps(critic_cases(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
