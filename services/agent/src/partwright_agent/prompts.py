import json
from collections.abc import Sequence
from typing import Any

DESIGN_RULES = """You are a mechanical design engineer. You write parametric CAD models as JSON in the Partwright IR.

Units: millimetres and degrees. Z is up.
Parameters: every dimension the user gives, and every important derived one, is a parameter with a snake_case name, a value, a unit ("mm", "deg" or "" for counts), a short description and provenance {"source": "prompt", "quote": "<words from the request>"}, {"source": "standard", "ref": "<standard>"} or {"source": "default"} if you chose it. Features reference parameters with expressions such as "plate_length / 2 - hole_margin".
How to model:
- Plates, brackets, flanges and boxes: draw the outline on the plane of the largest face and extrude it. A plate is a rect (or circle) on XY extruded by its thickness.
- Bent or angled profiles (L, U, T sections, gussets): draw the cross-section as a polygon on XZ and extrude it symmetric by the width.
- Turned parts (bushings, shafts, spacers): draw the half cross-section as a polygon on XZ with every x > 0 and revolve it about axis Y.
- Holes are always hole features, never revolves or circle cuts.
- Hollow boxes and cups: extrude the outside, then shell with the open face.
Sketch planes: XY (sketch x -> X, sketch y -> Y, offset moves +Z), XZ (sketch x -> X, sketch y -> Z, offset moves -Y), YZ (sketch x -> Y, sketch y -> Z, offset moves +X). Rect and circle are centred on "center". Polygon points are absolute sketch coordinates. A circle with "subtract": true cuts a ring.
Features run in order on one solid per part. The first feature of a part must be an extrude or revolve with mode "add". Extrude distance may be negative to go the other way; symmetric=true centres the extrusion on the plane.
Holes: "plane" is where the drill enters, "at" gives the centres in that plane's sketch coordinates, depth null means through all. Use grid for rectangular patterns (centred on "center"), polar for bolt circles (diameter = pitch circle), points for anything else.
Clearance holes (ISO 273 medium): M2 2.4, M2.5 2.9, M3 3.4, M4 4.5, M5 5.5, M6 6.6, M8 9.0, M10 11.0, M12 13.5. Tap drills: M3 2.5, M4 3.3, M5 4.2, M6 5.0, M8 6.8.
Fillet/chamfer edge sets: all, top, bottom, parallel_x, parallel_y, parallel_z. Keep radii smaller than half the thinnest wall.
Model only what was asked; do not add decorative features. Give the design a short descriptive title.
Answer with JSON only."""


def _p(name: str, value: float, unit: str, description: str, quote: str | None = None, ref: str | None = None) -> dict[str, Any]:
    source = {"source": "prompt", "quote": quote} if quote else {"source": "standard", "ref": ref} if ref else {"source": "default"}
    return {"name": name, "value": value, "unit": unit, "description": description, "provenance": source}


def _part(pid: str, name: str, sketches: list[dict[str, Any]], features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": pid, "name": name, "sketches": sketches, "features": features}]


EXAMPLES: list[tuple[str, dict[str, Any]]] = [
    (
        "Round cover plate, 100 mm diameter, 6 mm thick, 6x M5 holes on an 80 mm bolt circle, 30 mm centre bore, 1 mm chamfer on the top edges.",
        {
            "title": "Round cover plate",
            "params": [
                _p("plate_diameter", 100, "mm", "outer diameter", "100 mm diameter"),
                _p("thickness", 6, "mm", "plate thickness", "6 mm thick"),
                _p("bolt_count", 6, "", "number of bolts", "6x M5"),
                _p("bolt_hole_diameter", 5.5, "mm", "M5 clearance", ref="ISO 273"),
                _p("bolt_circle_diameter", 80, "mm", "pitch circle", "80 mm bolt circle"),
                _p("bore_diameter", 30, "mm", "centre bore", "30 mm centre bore"),
                _p("edge_chamfer", 1, "mm", "top edge chamfer", "1 mm chamfer"),
            ],
            "parts": _part(
                "cover",
                "Cover plate",
                [
                    {
                        "id": "disc",
                        "plane": {"base": "XY", "offset": 0},
                        "entities": [{"kind": "circle", "center": [0, 0], "diameter": "plate_diameter"}],
                    }
                ],
                [
                    {"kind": "extrude", "id": "body", "name": "Plate body", "sketch": "disc", "distance": "thickness", "mode": "add"},
                    {
                        "kind": "hole",
                        "id": "bore",
                        "name": "Centre bore",
                        "plane": {"base": "XY", "offset": "thickness"},
                        "at": {"kind": "points", "points": [[0, 0]]},
                        "diameter": "bore_diameter",
                        "depth": None,
                    },
                    {
                        "kind": "hole",
                        "id": "bolt_holes",
                        "name": "Bolt holes",
                        "plane": {"base": "XY", "offset": "thickness"},
                        "at": {
                            "kind": "polar",
                            "center": [0, 0],
                            "count": "bolt_count",
                            "diameter": "bolt_circle_diameter",
                            "start_angle": 0,
                        },
                        "diameter": "bolt_hole_diameter",
                        "depth": None,
                    },
                    {"kind": "chamfer", "id": "top_chamfer", "name": "Top edge chamfer", "edges": "top", "length": "edge_chamfer"},
                ],
            ),
        },
    ),
    (
        "Angle bracket from 5 mm steel, legs 50 mm and 40 mm, 30 mm wide, one M8 hole in the middle of each leg.",
        {
            "title": "Angle bracket",
            "params": [
                _p("base_leg", 50, "mm", "horizontal leg length", "legs 50 mm"),
                _p("upright_leg", 40, "mm", "vertical leg height", "and 40 mm"),
                _p("width", 30, "mm", "bracket width", "30 mm wide"),
                _p("thickness", 5, "mm", "plate thickness", "5 mm steel"),
                _p("hole_diameter", 9.0, "mm", "M8 clearance", ref="ISO 273"),
            ],
            "parts": _part(
                "bracket",
                "Angle bracket",
                [
                    {
                        "id": "profile",
                        "plane": {"base": "XZ", "offset": 0},
                        "entities": [
                            {
                                "kind": "polygon",
                                "points": [
                                    [0, 0],
                                    ["base_leg", 0],
                                    ["base_leg", "thickness"],
                                    ["thickness", "thickness"],
                                    ["thickness", "upright_leg"],
                                    [0, "upright_leg"],
                                ],
                            }
                        ],
                    }
                ],
                [
                    {"kind": "extrude", "id": "body", "name": "L profile", "sketch": "profile", "distance": "width", "symmetric": True},
                    {
                        "kind": "hole",
                        "id": "base_hole",
                        "name": "Base leg hole",
                        "plane": {"base": "XY", "offset": "thickness"},
                        "at": {"kind": "points", "points": [["thickness + (base_leg - thickness) / 2", 0]]},
                        "diameter": "hole_diameter",
                        "depth": None,
                    },
                    {
                        "kind": "hole",
                        "id": "upright_hole",
                        "name": "Upright leg hole",
                        "plane": {"base": "YZ", "offset": "thickness"},
                        "at": {"kind": "points", "points": [[0, "thickness + (upright_leg - thickness) / 2"]]},
                        "diameter": "hole_diameter",
                        "depth": None,
                    },
                ],
            ),
        },
    ),
    (
        "Open-top tray, outside 80 x 50 x 20 mm, 2 mm walls, 3 mm radius on the vertical corners.",
        {
            "title": "Open-top tray",
            "params": [
                _p("length", 80, "mm", "outside length", "80 x 50 x 20 mm"),
                _p("width", 50, "mm", "outside width", "80 x 50 x 20 mm"),
                _p("height", 20, "mm", "outside height", "80 x 50 x 20 mm"),
                _p("wall", 2, "mm", "wall and floor thickness", "2 mm walls"),
                _p("corner_radius", 3, "mm", "vertical corner radius", "3 mm radius"),
            ],
            "parts": _part(
                "tray",
                "Tray",
                [
                    {
                        "id": "outline",
                        "plane": {"base": "XY", "offset": 0},
                        "entities": [{"kind": "rect", "center": [0, 0], "width": "length", "height": "width"}],
                    }
                ],
                [
                    {"kind": "extrude", "id": "block", "name": "Outer block", "sketch": "outline", "distance": "height"},
                    {"kind": "fillet", "id": "corners", "name": "Corner radius", "edges": "parallel_z", "radius": "corner_radius"},
                    {"kind": "shell", "id": "hollow", "name": "Shell", "open_face": "top", "thickness": "wall"},
                ],
            ),
        },
    ),
    (
        "Flanged bushing: 20 mm bore, 30 mm outside diameter, 25 mm long overall, 45 mm flange 5 mm thick.",
        {
            "title": "Flanged bushing",
            "params": [
                _p("bore_diameter", 20, "mm", "bore", "20 mm bore"),
                _p("outer_diameter", 30, "mm", "shank diameter", "30 mm outside diameter"),
                _p("length", 25, "mm", "overall length", "25 mm long overall"),
                _p("flange_diameter", 45, "mm", "flange diameter", "45 mm flange"),
                _p("flange_thickness", 5, "mm", "flange thickness", "5 mm thick"),
            ],
            "parts": _part(
                "bushing",
                "Bushing",
                [
                    {
                        "id": "half_section",
                        "plane": {"base": "XZ", "offset": 0},
                        "entities": [
                            {
                                "kind": "polygon",
                                "points": [
                                    ["bore_diameter / 2", 0],
                                    ["flange_diameter / 2", 0],
                                    ["flange_diameter / 2", "flange_thickness"],
                                    ["outer_diameter / 2", "flange_thickness"],
                                    ["outer_diameter / 2", "length"],
                                    ["bore_diameter / 2", "length"],
                                ],
                            }
                        ],
                    }
                ],
                [{"kind": "revolve", "id": "body", "name": "Turned body", "sketch": "half_section", "axis": "Y", "angle": 360}],
            ),
        },
    ),
]

REQUIREMENT_RULES = """Extract the checkable geometric requirements from a mechanical design request.
kind "extent": an overall outside dimension of the finished part (length, width, height, diameter, thickness of a plate) with value in mm.
kind "holes": a number of holes and their allowed diameter range in mm. For a metric screw clearance hole use the ISO 273 fine-to-coarse range: M3 3.2-3.6, M4 4.3-4.8, M5 5.3-5.8, M6 6.4-7.0, M8 8.4-10.0, M10 10.5-12.0, M12 13.0-14.5. For an explicit hole diameter use +-0.1.
kind "hole_spacing": a stated distance between hole centres in mm (pitch, bolt spacing, square pattern side).
kind "wall": a stated wall thickness of a tube or ring in mm.
One requirement per number: "80x60 plate" is two extents, 80 and 60. A plate or sheet thickness is an extent, not a wall.
Only include what the request states. Do not invent requirements. Answer with JSON only."""

REQUIREMENT_EXAMPLE = (
    "Base plate 120 x 40 mm, 8 mm thick, six M8 holes at 30 mm pitch, plus a 2 mm wall sleeve.",
    {
        "requirements": [
            {"kind": "extent", "description": "length 120", "value": 120},
            {"kind": "extent", "description": "width 40", "value": 40},
            {"kind": "extent", "description": "thickness 8", "value": 8},
            {"kind": "holes", "description": "six M8 clearance holes", "count": 6, "diameter_min": 8.4, "diameter_max": 10.0},
            {"kind": "hole_spacing", "description": "30 mm pitch", "value": 30},
            {"kind": "wall", "description": "sleeve wall 2", "value": 2},
        ]
    },
)


def design_messages(request: str, reference: Sequence[str] = ()) -> list[tuple[str, str]]:
    shots = [m for req, design in EXAMPLES for m in (("user", req), ("assistant", json.dumps(design)))]
    return [("system", DESIGN_RULES), *shots, ("user", _with_reference(request, reference))]


def _with_reference(request: str, reference: Sequence[str]) -> str:
    if not reference:
        return request
    return request + "\n\nReference data:\n" + "\n".join(f"- {r}" for r in reference)


def requirement_messages(request: str) -> list[tuple[str, str]]:
    example, answer = REQUIREMENT_EXAMPLE
    return [("system", REQUIREMENT_RULES), ("user", example), ("assistant", json.dumps(answer)), ("user", request)]


def repair_message(problems: list[str], unchanged: bool) -> str:
    listed = "\n".join(f"- {p}" for p in problems)
    again = (
        "Your last answer was identical to the one before it. You must change the parts that cause these problems.\n" if unchanged else ""
    )
    return f"{again}The design has problems:\n{listed}\nReturn the complete corrected design as JSON. Keep everything that was right."


def refine_message(design_json: str, instruction: str) -> str:
    return (
        f"Current design:\n{design_json}\n\nChange request: {instruction}\n\n"
        'If the change only needs new parameter values, answer {"updates": [{"name": ..., "value": ...}], "design": null}. '
        'Otherwise answer {"updates": [], "design": <the complete new design>}. Keep every parameter and feature the request does not mention.'
    )
