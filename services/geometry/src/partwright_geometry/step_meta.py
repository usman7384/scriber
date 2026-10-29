import re
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from build123d import CenterOf, Face, Shape, Vector
from OCP.collections import Sequence_TDF_Label
from OCP.IFSelect import IFSelect_ReturnStatus
from OCP.Interface import Interface_Static
from OCP.ShapeUpgrade import ShapeUpgrade_RemoveLocations
from OCP.STEPCAFControl import STEPCAFControl_Controller, STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_StepModelType
from OCP.TCollection import TCollection_ExtendedString, TCollection_HAsciiString
from OCP.TDataStd import TDataStd_Name, TDataStd_TreeNode
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc, XCAFDoc_DocumentTool, XCAFDoc_Material, XCAFDoc_ShapeTool
from OCP.XSControl import XSControl_WorkSession

from partwright_geometry.mass import density
from partwright_geometry.models import FaceGroupInfo, StepBody, StepMetadata

AP242 = 5
SCHEMA = re.compile(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'")
FaceGroups = dict[str, list[Face]]
Materials = dict[str, str | None]


def write_step(parts: dict[str, Shape[Any]], title: str, faces: dict[str, FaceGroups], materials: Materials, path: Path) -> None:
    doc = _document()
    shapes = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    root = shapes.NewShape()
    _set_name(root, title)
    for pid, shape in parts.items():
        # the STEP writer drops names of faces that carry their own location, so bake locations in first
        flat = ShapeUpgrade_RemoveLocations()
        flat.Remove(shape.wrapped)
        label = shapes.AddShape(flat.GetResult(), False, False)
        _set_name(label, shape.label or pid)
        _name_faces(shapes, label, flat, faces.get(pid, {}))
        if material := materials.get(pid):
            _set_material(doc, label, material)
        shapes.AddComponent(root, label, TopLoc_Location())
    shapes.UpdateAssemblies()
    writer = STEPCAFControl_Writer(XSControl_WorkSession(), False)
    writer.SetNameMode(True)
    writer.SetMaterialMode(True)
    with _statics({"write.step.schema": AP242, "write.stepcaf.subshapes.name": 1}):
        writer.Transfer(doc, STEPControl_StepModelType.STEPControl_AsIs)
        if writer.Write(str(path)) != IFSelect_ReturnStatus.IFSelect_RetDone:
            raise RuntimeError(f"could not write {path.name}")


def read_step(path: Path) -> StepMetadata:
    doc = _document()
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetMatMode(True)
    with _statics({"read.stepcaf.subshapes.name": 1}):
        if reader.ReadFile(str(path)) != IFSelect_ReturnStatus.IFSelect_RetDone or not reader.Transfer(doc):
            raise ValueError(f"{path.name} is not a readable STEP file")
    shapes = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    bodies = [b for label in _labels(shapes.GetFreeShapes) for b in _bodies(label, TopLoc_Location(), [])]
    header = path.read_text(encoding="utf-8", errors="replace")[:4000]
    match = SCHEMA.search(header)
    return StepMetadata(schema_name=match.group(1).split()[0] if match else "", bodies=bodies)


def _document() -> TDocStd_Document:
    STEPCAFControl_Controller.Init_s()
    doc = TDocStd_Document(TCollection_ExtendedString("XmlXCAF"))
    XCAFApp_Application.GetApplication_s().InitDocument(doc)
    return doc


def _name_faces(shapes: XCAFDoc_ShapeTool, label: TDF_Label, flat: ShapeUpgrade_RemoveLocations, groups: FaceGroups) -> None:
    owner: dict[Face, str] = {}
    for group, members in groups.items():
        for face in members:
            if face in owner:
                raise ValueError(f"a face is in both {owner[face]!r} and {group!r}")
            owner[face] = group
            sub = shapes.AddSubShape(label, flat.ModifiedShape(face.wrapped))
            if sub.IsNull():
                raise ValueError(f"face group {group!r}: a face is not part of the body")
            _set_name(sub, group)


def _set_material(doc: TDocStd_Document, label: TDF_Label, material: str) -> None:
    tool = XCAFDoc_DocumentTool.MaterialTool_s(doc.Main())
    rho = density(material)
    h = TCollection_HAsciiString
    tool.SetMaterial(label, h(material), h(""), rho or 0.0, h("g/cm3" if rho else ""), h("POSITIVE_RATIO"))


def _bodies(label: TDF_Label, loc: TopLoc_Location, path: list[str]) -> Iterator[StepBody]:
    path = [*path, _get_name(label)]
    if XCAFDoc_ShapeTool.IsAssembly_s(label):
        for component in _labels(lambda seq: XCAFDoc_ShapeTool.GetComponents_s(label, seq, False)):
            referred = TDF_Label()
            XCAFDoc_ShapeTool.GetReferredShape_s(component, referred)
            yield from _bodies(referred, loc * XCAFDoc_ShapeTool.GetLocation_s(component), path)
        return
    material, rho = _material(label)
    yield StepBody(name=path[-1], path="/".join(path), material=material, density_g_cm3=rho, face_groups=_face_groups(label, loc))


def _face_groups(label: TDF_Label, loc: TopLoc_Location) -> list[FaceGroupInfo]:
    groups: dict[str, list[Face]] = defaultdict(list)
    for sub in _labels(lambda seq: XCAFDoc_ShapeTool.GetSubShapes_s(label, seq)):
        shape = XCAFDoc_ShapeTool.GetShape_s(sub)
        if name := _get_name(sub):
            groups[name].append(Face(TopoDS.Face(shape.Moved(loc))))
    return [_group(name, faces) for name, faces in groups.items()]


def _group(name: str, faces: list[Face]) -> FaceGroupInfo:
    area = sum(f.area for f in faces)
    center = sum((f.center(CenterOf.MASS) * f.area for f in faces), Vector()) / area
    normals = {tuple(round(c, 6) + 0.0 for c in f.normal_at(f.center())) for f in faces if f.geom_type.name == "PLANE"}
    normal = next(iter(normals)) if len(normals) == 1 and all(f.geom_type.name == "PLANE" for f in faces) else None
    return FaceGroupInfo(name=name, faces=len(faces), area=area, center=(center.X, center.Y, center.Z), normal=normal)


def _material(label: TDF_Label) -> tuple[str | None, float | None]:
    # FindAttribute crashes in OCP when the attribute is missing, so test with IsAttribute first
    node, material = TDataStd_TreeNode(), XCAFDoc_Material()
    if not label.IsAttribute(XCAFDoc.MaterialRefGUID_s()):
        return None, None
    label.FindAttribute(XCAFDoc.MaterialRefGUID_s(), node)
    if not (node.HasFather() and node.Father().Label().IsAttribute(XCAFDoc_Material.GetID_s())):
        return None, None
    node.Father().Label().FindAttribute(XCAFDoc_Material.GetID_s(), material)
    rho = material.GetDensity()
    return material.GetName().ToCString(), rho if rho > 0 else None


def _labels(fill: Any) -> list[TDF_Label]:
    seq = Sequence_TDF_Label()
    fill(seq)
    return [seq.Value(i) for i in range(1, seq.Length() + 1)]


def _set_name(label: TDF_Label, name: str) -> None:
    TDataStd_Name.Set_s(label, TCollection_ExtendedString(name))


def _get_name(label: TDF_Label) -> str:
    attr = TDataStd_Name()
    if not label.IsAttribute(TDataStd_Name.GetID_s()):
        return ""
    label.FindAttribute(TDataStd_Name.GetID_s(), attr)
    return str(attr.Get().ToExtString())


@contextmanager
def _statics(values: dict[str, int]) -> Iterator[None]:
    # OCCT translation settings are process-wide; restore them so other exports keep their defaults
    before = {k: Interface_Static.IVal_s(k) for k in values}
    for k, v in values.items():
        Interface_Static.SetIVal_s(k, v)
    try:
        yield
    finally:
        for k, v in before.items():
            Interface_Static.SetIVal_s(k, v)
