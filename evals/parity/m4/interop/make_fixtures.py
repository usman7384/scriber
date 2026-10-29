from pathlib import Path

from build123d import Align, Box, Cylinder, Part, Pos
from OCP.Interface import Interface_Static
from OCP.STEPCAFControl import STEPCAFControl_Controller, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_StepModelType
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
from OCP.XSControl import XSControl_WorkSession

HERE = Path(__file__).parent
BOTTOM = (Align.CENTER, Align.CENTER, Align.MIN)
AP242 = 5
Tree = Part | list[tuple[str, "Tree"]]


def part_studio() -> Tree:
    bracket = Box(80, 60, 6, align=BOTTOM) + Cylinder(10, 21, align=BOTTOM)
    for x in (-30, 30):
        for y in (-20, 20):
            bracket -= Pos(x, y, 0) * Cylinder(3.3, 100)
    return [("Bracket", bracket), ("Pin", Pos(70, 0, 0) * Cylinder(4, 30.48, align=BOTTOM))]


def gearbox() -> Tree:
    bearing = Pos(0, 0, 10) * (Cylinder(14, 12, align=BOTTOM) - Cylinder(6, 12, align=BOTTOM))
    shafts: Tree = [("shaft", Pos(0, 0, 10) * Cylinder(6, 60, align=BOTTOM)), ("bearing", bearing)]
    return [
        ("base_plate", Box(120, 80, 10, align=BOTTOM)),
        ("shaft_assembly", shafts),
        ("cover", Pos(0, 0, 70) * Box(120, 80, 4, align=BOTTOM)),
    ]


def write_ap242(path: Path, title: str, tree: Tree) -> None:
    # written through XCAF rather than build123d's exporter, whose header always names the AP214 schema
    STEPCAFControl_Controller.Init_s()
    doc = TDocStd_Document(TCollection_ExtendedString("XmlXCAF"))
    XCAFApp_Application.GetApplication_s().InitDocument(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    _add(tool, title, tree)
    tool.UpdateAssemblies()
    Interface_Static.SetIVal_s("write.step.schema", AP242)
    writer = STEPCAFControl_Writer(XSControl_WorkSession(), False)
    writer.SetNameMode(True)
    writer.Transfer(doc, STEPControl_StepModelType.STEPControl_AsIs)
    writer.Write(str(path))


def _add(tool: XCAFDoc_ShapeTool, name: str, node: Tree) -> TDF_Label:
    if isinstance(node, list):
        label = tool.NewShape()
        for child_name, child in node:
            tool.AddComponent(label, _add(tool, child_name, child), TopLoc_Location())
    else:
        label = tool.AddShape(node.wrapped, False, False)
    TDataStd_Name.Set_s(label, TCollection_ExtendedString(name))
    return label


if __name__ == "__main__":
    write_ap242(HERE / "onshape" / "part_studio.step", "Part Studio 1", part_studio())
    write_ap242(HERE / "gearbox_ap242.step", "gearbox", gearbox())
