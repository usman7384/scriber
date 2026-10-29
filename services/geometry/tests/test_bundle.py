import zipfile
from pathlib import Path
from typing import Any

import pytest

from partwright_geometry import LocalGeometry, export_bundle, open_bundle
from partwright_ir import Design


def test_bundle_reopens_with_features_constraints_and_step(geometry: LocalGeometry, plate: dict[str, Any], tmp_path: Path) -> None:
    design = Design.model_validate(plate)
    art = geometry.build(design, tmp_path / "build")
    bundle = open_bundle(export_bundle(design, art.files["step"], tmp_path / "plate.zip"))
    assert bundle.design == design
    assert [(f.id, f.name, f.depends_on) for f in bundle.features] == [("base", "Base", ["s", "XY"]), ("boss", "Boss", ["b", "base.end"])]
    assert [(s.sketch, s.dof) for s in bundle.sketches] == [("s", 0), ("b", 0)]
    assert {"design.json", "model.py", "params.json", "features.json", "sketches.json", "model.step"} <= set(bundle.files)


def test_edited_design_without_a_new_hash_is_rejected(geometry: LocalGeometry, plate: dict[str, Any], tmp_path: Path) -> None:
    design = Design.model_validate(plate)
    art = geometry.build(design, tmp_path / "build")
    good = export_bundle(design, art.files["step"], tmp_path / "plate.zip")
    bad = tmp_path / "edited.zip"
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(bad, "w") as dst:
        for item in src.namelist():
            data = src.read(item)
            dst.writestr(item, data.replace(b'"value": 10.0', b'"value": 12.0') if item == "design.json" else data)
    with pytest.raises(ValueError, match="does not match the manifest hash"):
        open_bundle(bad)
