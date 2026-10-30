from pathlib import Path

from partwright_api import thumbnail_targets


def test_thumbnail_targets_are_every_built_version(tmp_path: Path) -> None:
    for version in ("m1/v1", "m1/v2", "m2/v1"):
        (tmp_path / "models" / version).mkdir(parents=True)
    for built in ("m1/v2", "m2/v1"):
        (tmp_path / "models" / built / "model.glb").touch()
    targets = thumbnail_targets(tmp_path)
    assert [png.relative_to(tmp_path).as_posix() for _, png in targets] == ["models/m1/v2/thumbnail.png", "models/m2/v1/thumbnail.png"]
    assert all(glb.parent == png.parent for glb, png in targets)
