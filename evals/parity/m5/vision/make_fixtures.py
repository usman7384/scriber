import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
INK, SIZE, SCALE = (20, 20, 30), (1100, 800), 3.2
Point = tuple[float, float]
PLATES: dict[str, dict[str, float]] = {
    "plate_a": {"length": 140, "width": 90, "thickness": 6, "hole_d": 9, "pitch_x": 120, "pitch_y": 70},
    "plate_b": {"length": 160, "width": 100, "thickness": 8, "hole_d": 6.6, "pitch_x": 130, "pitch_y": 80},
    "plate_c": {"length": 120, "width": 120, "thickness": 10, "hole_d": 11, "pitch_x": 90, "pitch_y": 90},
    "plate_d": {"length": 200, "width": 80, "thickness": 5, "hole_d": 5.5, "pitch_x": 170, "pitch_y": 50},
}
FLANGES: dict[str, dict[str, float]] = {
    "flange_a": {"od": 150, "pcd": 110, "bolt_count": 4, "hole_d": 18, "bore": 49, "thickness": 16},
    "flange_b": {"od": 200, "pcd": 160, "bolt_count": 8, "hole_d": 18, "bore": 90, "thickness": 20},
    "flange_c": {"od": 130, "pcd": 100, "bolt_count": 6, "hole_d": 9, "bore": 50, "thickness": 12},
    "flange_d": {"od": 180, "pcd": 140, "bolt_count": 8, "hole_d": 13.5, "bore": 76, "thickness": 14},
}


def font(size: int = 26) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def arrow(draw: ImageDraw.ImageDraw, a: Point, b: Point) -> None:
    draw.line([a, b], fill=INK, width=2)
    for tip, tail in ((a, b), (b, a)):
        ang = math.atan2(tail[1] - tip[1], tail[0] - tip[0])
        wing = [(tip[0] + 14 * math.cos(ang + s), tip[1] + 14 * math.sin(ang + s)) for s in (0.3, -0.3)]
        draw.polygon([tip, *wing], fill=INK)


def label(draw: ImageDraw.ImageDraw, at: Point, text: str) -> None:
    w = draw.textlength(text, font=font())
    draw.rectangle([at[0] - w / 2 - 4, at[1] - 16, at[0] + w / 2 + 4, at[1] + 16], fill="white")
    draw.text((at[0] - w / 2, at[1] - 14), text, fill=INK, font=font())


def dim(draw: ImageDraw.ImageDraw, a: Point, b: Point, text: str) -> None:
    arrow(draw, a, b)
    label(draw, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), text)


def hole(draw: ImageDraw.ImageDraw, c: Point, d: float) -> None:
    r = d / 2 * SCALE
    draw.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=INK, width=2)
    draw.line([(c[0] - r - 6, c[1]), (c[0] + r + 6, c[1])], fill=INK, width=1)
    draw.line([(c[0], c[1] - r - 6), (c[0], c[1] + r + 6)], fill=INK, width=1)


def sheet(title: str, note: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", SIZE, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([10, 10, SIZE[0] - 10, SIZE[1] - 10], outline=INK, width=3)
    draw.text((30, SIZE[1] - 100), f"{title}   all dimensions in mm", fill=INK, font=font(24))
    draw.text((30, SIZE[1] - 60), note, fill=INK, font=font(24))
    return image, draw


def plate(name: str, v: dict[str, float]) -> Image.Image:
    image, draw = sheet(name.upper().replace("_", " "), f"THICKNESS {v['thickness']:g}   4 HOLES DIA {v['hole_d']:g} THRU")
    cx, cy, hw, hh = 500, 340, v["length"] / 2 * SCALE, v["width"] / 2 * SCALE
    draw.rectangle([cx - hw, cy - hh, cx + hw, cy + hh], outline=INK, width=4)
    px, py = v["pitch_x"] / 2 * SCALE, v["pitch_y"] / 2 * SCALE
    for sx in (-1, 1):
        for sy in (-1, 1):
            hole(draw, (cx + sx * px, cy + sy * py), v["hole_d"])
    dim(draw, (cx - hw, cy + hh + 60), (cx + hw, cy + hh + 60), f"{v['length']:g}")
    dim(draw, (cx - px, cy + hh + 25), (cx + px, cy + hh + 25), f"{v['pitch_x']:g}")
    dim(draw, (cx + hw + 100, cy - hh), (cx + hw + 100, cy + hh), f"{v['width']:g}")
    dim(draw, (cx + hw + 30, cy - py), (cx + hw + 30, cy + py), f"{v['pitch_y']:g}")
    return image


def flange(name: str, v: dict[str, float]) -> Image.Image:
    note = f"THICKNESS {v['thickness']:g}   {v['bolt_count']:g} HOLES DIA {v['hole_d']:g} EQUALLY SPACED ON PCD {v['pcd']:g}"
    image, draw = sheet(name.upper().replace("_", " "), note)
    c, s = (480.0, 330.0), SCALE * 0.85
    for d, width in ((v["od"], 4), (v["bore"], 3)):
        r = d / 2 * s
        draw.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=INK, width=width)
    r = v["pcd"] / 2 * s
    draw.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(120, 120, 140), width=1)
    n = round(v["bolt_count"])
    for k in range(n):
        a = math.radians(90 + 360 * k / n + 180 / n)
        rr = v["hole_d"] / 2 * s
        p = (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
        draw.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], outline=INK, width=2)
    ro = v["od"] / 2 * s
    dim(draw, (c[0] - ro, c[1] + ro + 40), (c[0] + ro, c[1] + ro + 40), f"DIA {v['od']:g}")
    rb = v["bore"] / 2 * s
    dim(draw, (c[0] - rb, c[1]), (c[0] + rb, c[1]), f"DIA {v['bore']:g}")
    return image


def main() -> None:
    truth: dict[str, dict[str, float]] = {}
    for name, v in PLATES.items():
        plate(name, v).save(HERE / f"{name}.png")
        truth[name] = v
    for name, v in FLANGES.items():
        flange(name, v).save(HERE / f"{name}.png")
        truth[name] = v
    (HERE / "truth.json").write_text(json.dumps(truth, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
