from pathlib import Path

from PIL import Image

from partwright_geometry import LocalGeometry
from partwright_geometry.worker import handle
from partwright_ir import Design

PLATE = Design.model_validate(
    {
        "title": "Plate",
        "params": [],
        "parts": [
            {
                "id": "p",
                "name": "P",
                "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": 40, "height": 20}]}],
                "features": [{"kind": "extrude", "id": "e", "name": "E", "sketch": "s", "distance": 5}],
            }
        ],
    }
)


def test_thumbnail_is_a_256_px_png(geometry: LocalGeometry, tmp_path: Path) -> None:
    art = geometry.build(PLATE, tmp_path)
    png = geometry.thumbnail(art.files["glb"], tmp_path / "thumbnail.png")
    with Image.open(png) as image:
        assert (image.format, image.size) == ("PNG", (256, 256))
        assert len(set(image.getdata())) > 2


def test_thumbnail_of_a_missing_file_is_an_error_reply(tmp_path: Path) -> None:
    reply = handle({"op": "thumbnail", "path": str(tmp_path / "none.glb"), "png": str(tmp_path / "t.png"), "size": 64})
    assert not reply["ok"]
