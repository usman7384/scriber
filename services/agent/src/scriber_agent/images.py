import io

from PIL import Image, UnidentifiedImageError

# hosted vision models shrink an image to about 1,500 px on its long side; a 3,000 px drawing loses its small dimension text
LARGE = 2000
OVERLAP = 0.1

TILE_NOTE = """
After the first image come enlarged quarters of it (top-left, top-right, bottom-left, bottom-right),
overlapping a little: read small dimension text from them."""


def with_tiles(images: tuple[bytes, ...]) -> tuple[bytes, ...]:
    return tuple(part for image in images for part in (image, *_quarters(image)))


def _quarters(image: bytes) -> list[bytes]:
    try:
        opened = Image.open(io.BytesIO(image))
    except UnidentifiedImageError:
        return []  # a format Pillow cannot read still goes to the model whole; only tiling is skipped
    with opened as im:
        w, h = im.size
        if max(w, h) < LARGE:
            return []
        dx, dy = int(w * OVERLAP / 2), int(h * OVERLAP / 2)
        left, right, top, bottom = (0, w // 2 + dx), (w // 2 - dx, w), (0, h // 2 + dy), (h // 2 - dy, h)
        boxes = [(x[0], y[0], x[1], y[1]) for y in (top, bottom) for x in (left, right)]
        return [_png(im.crop(b)) for b in boxes]


def _png(im: Image.Image) -> bytes:
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()
