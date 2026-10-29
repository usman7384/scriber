import sys
from pathlib import Path

from PIL import Image

# web parity screenshots in story order: prompt, model, edit, checks, context, assembly, sharing
FRAMES = (
    "WP-2/1-attached.png",
    "WP-2/2-generated.png",
    "WP-1/1-iso.png",
    "WP-1/3-orbited.png",
    "PR-3/3-on-applied.png",
    "VM-4/popup.png",
    "PR-6/2-offset-applied.png",
    "AS-1/2-picked-cube.png",
    "CX-5/1-graph.png",
    "WP-10/2-community.png",
    "WP-14/1-done.png",
)


def main(evidence: Path, out: Path, width: int = 960) -> None:
    frames = []
    for name in FRAMES:
        with Image.open(evidence / name) as im:
            rgb = im.convert("RGB")
        frames.append(rgb.resize((width, round(rgb.height * width / rgb.width))).quantize(colors=128))
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=2200, loop=0, optimize=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
