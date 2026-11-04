import json
import zipfile
from pathlib import Path

from pydantic import TypeAdapter

from scriber_geometry.models import Bundle, FeatureEntry, SketchDof
from scriber_geometry.sketcher import remaining_dof, sketch_dof
from scriber_ir import Design, compile_design, design_hash
from scriber_ir.model import (
    Chamfer,
    Extrude,
    Feature,
    Fillet,
    Groove,
    Hole,
    Keyway,
    Lid,
    Loft,
    Part,
    Pattern,
    Revolve,
    Shell,
    ShellWithLid,
)

FORMAT = "scriber-bundle"
FEATURES = TypeAdapter(list[FeatureEntry])
SKETCHES = TypeAdapter(list[SketchDof])


def export_bundle(design: Design, step: Path, out: Path) -> Path:
    files = {
        "design.json": design.model_dump_json(indent=2),
        "model.py": compile_design(design),
        "params.json": json.dumps([p.model_dump(mode="json") for p in design.params], indent=2),
        "features.json": FEATURES.dump_json(feature_tree(design), indent=2).decode(),
        "sketches.json": SKETCHES.dump_json(sketch_dof(design), indent=2).decode(),
    }
    manifest = {"format": FORMAT, "version": 1, "title": design.title, "design_hash": design_hash(design), "files": [*files, "model.step"]}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2))
        for name, text in files.items():
            z.writestr(name, text)
        z.write(step, "model.step")
    return out


def open_bundle(path: Path) -> Bundle:
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read("manifest.json"))
        if manifest.get("format") != FORMAT:
            raise ValueError(f"{path.name} is not a {FORMAT}")
        design = Design.model_validate_json(z.read("design.json"))
        if design_hash(design) != manifest["design_hash"]:
            raise ValueError(f"{path.name}: design.json does not match the manifest hash")
        if compile_design(design) != z.read("model.py").decode():
            raise ValueError(f"{path.name}: model.py does not replay from design.json")
        sketches = SKETCHES.validate_json(z.read("sketches.json"))
        features = FEATURES.validate_json(z.read("features.json"))
        names = z.namelist()
    for s in sketches:
        if s.dof is not None and remaining_dof(s.geometry, s.constraints) != s.dof:
            raise ValueError(f"{path.name}: sketch {s.sketch} constraints do not give the recorded DOF")
    return Bundle(title=design.title, design_hash=manifest["design_hash"], design=design, features=features, sketches=sketches, files=names)


def feature_tree(design: Design) -> list[FeatureEntry]:
    return [FeatureEntry(part=p.id, id=f.id, name=f.name, kind=f.kind, depends_on=_depends(p, f)) for p in design.parts for f in p.features]


def _depends(part: Part, f: Feature) -> list[str]:
    sketches = {s.id: s for s in part.sketches}
    match f:
        case Extrude() | Revolve():
            return [f.sketch, sketches[f.sketch].plane.ref]
        case Hole():
            return [f.plane.ref]
        case Pattern():
            return f.features
        case Fillet() | Chamfer():
            return [f.edges.of]
        case Shell():
            return [s.of for s in f.open]
        case Loft():
            return f.sections
        case Keyway() | Groove() | Lid():
            return [f.of]
        case ShellWithLid():
            return []
        case _:
            return [f.plane.ref]
