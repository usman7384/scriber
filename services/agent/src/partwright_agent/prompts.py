import json
from collections.abc import Sequence
from typing import Any

DESIGN_RULES = """You are a mechanical design engineer. You write parametric CAD models as JSON in the Partwright IR (ir_version 2).

Units: millimetres and degrees. Z is up, -Y is the front.
Parameters: every dimension the user gives, and every important derived one, is a parameter with a snake_case name, a value, a unit ("mm", "deg" or "" for counts), a short description and provenance {"source": "prompt", "quote": "<words from the request>"}, {"source": "standard", "ref": "<standard>"} or {"source": "default"}. Features reference parameters with expressions such as "plate_length / 2 - hole_margin".
Planes ("plane": {"ref": ..., "offset": ...}) for sketches and holes:
- "XY" (sketch x -> X, y -> Y), "XZ" (x -> X, y -> Z), "YZ" (x -> Y, y -> Z), offset along the plane normal.
- A face of an earlier feature: "<feature id>.<face>" or "part.<face>", face = top, bottom, front, back, left, right, or start / end of an extrude. Sketch coordinates on a face are the same as on the matching base plane (top/bottom like XY, front/back like XZ, left/right like YZ). Offset moves outward from the face.
- A datum id from the part's "datums": base plane, offset, rotate_about x or y, angle; use it for sloped faces and angled holes.
How to model:
- Plates, blocks, flanges and boxes: outline on XY extruded by the thickness. Bosses, ribs, pockets and recesses: a sketch on the face they sit on, extruded "add" (outward) or "cut" (into the part).
- Bent or angled profiles (L, U, T sections): the cross-section as a polygon or path on XZ, extent "symmetric" by the width.
- Turned parts: the half section on XZ with every x > 0, revolved about axis Y.
- Outlines with arcs or rounded corners: a "path" entity (segments with "to", optional "arc" cw/ccw with "radius", optional corner "fillet").
- Every hole, port, bore and passage is a hole feature on the face it enters. Give "fastener" (e.g. "M6") and the compiler sizes it: type "simple" (clearance, fit close/normal/loose), "counterbore", "countersink", or "tapped" (tap drill, add "thread": "M6x1"). Otherwise give "diameter". depth null means through; blind holes may have drill_point "118". Passages that meet are holes from two faces whose depths reach each other.
- Repeated features: make one, then a "pattern" (linear with direction and spacing, polar about an axis, or mirror across a base plane).
- Hollow boxes: extrude the outside, then shell with the open faces.
Extrude extent: "blind" (distance; negative goes the other way on base planes), "symmetric", "two_sided" (distance and distance2), "through_all" (cuts only), "up_to_next". Mode add, cut or intersect.
Fillet, chamfer and shell faces use selectors: {"of": "part" or a feature id, "normal": "+z"..., "parallel": "x"/"y"/"z", "convexity": "concave"/"convex", "extreme": "max"/"min"}. Inside corners of a milled pocket: {"of": "<pocket>", "parallel": "z", "convexity": "concave"}. Top edges: {"normal": "+z", "extreme": "max"}. Keep radii smaller than half the thinnest wall.
Model only what was asked. Give the design a short descriptive title. Answer with JSON only."""


def _p(name: str, value: float, unit: str, description: str, quote: str | None = None, ref: str | None = None) -> dict[str, Any]:
    source = {"source": "prompt", "quote": quote} if quote else {"source": "standard", "ref": ref} if ref else {"source": "default"}
    return {"name": name, "value": value, "unit": unit, "description": description, "provenance": source}


def _design(title: str, params: list[dict[str, Any]], sketches: list[dict[str, Any]], features: list[dict[str, Any]]) -> dict[str, Any]:
    part = {"id": "part", "name": title, "sketches": sketches, "features": features}
    return {"ir_version": 2, "title": title, "params": params, "parts": [part]}


def _hole(hid: str, name: str, plane: str, at: dict[str, Any], **spec: Any) -> dict[str, Any]:
    return {"kind": "hole", "id": hid, "name": name, "plane": {"ref": plane}, "at": at, **spec}


def _at(*points: tuple[Any, Any]) -> dict[str, Any]:
    return {"kind": "points", "points": [list(p) for p in points]}


EXAMPLES: list[tuple[str, dict[str, Any]]] = [
    (
        "Round cover plate, 100 mm diameter, 6 mm thick, 6x M5 holes on an 80 mm bolt circle, 30 mm centre bore, 1 mm chamfer on the top edges.",
        _design(
            "Round cover plate",
            [
                _p("plate_diameter", 100, "mm", "outer diameter", "100 mm diameter"),
                _p("thickness", 6, "mm", "plate thickness", "6 mm thick"),
                _p("bolt_count", 6, "", "number of bolts", "6x M5"),
                _p("bolt_circle_diameter", 80, "mm", "pitch circle", "80 mm bolt circle"),
                _p("bore_diameter", 30, "mm", "centre bore", "30 mm centre bore"),
                _p("edge_chamfer", 1, "mm", "top edge chamfer", "1 mm chamfer"),
            ],
            [{"id": "disc", "plane": {"ref": "XY"}, "entities": [{"kind": "circle", "diameter": "plate_diameter"}]}],
            [
                {"kind": "extrude", "id": "plate", "name": "Plate", "sketch": "disc", "distance": "thickness"},
                _hole("bore", "Centre bore", "plate.top", _at((0, 0)), diameter="bore_diameter"),
                _hole(
                    "bolt_holes",
                    "M5 bolt holes",
                    "plate.top",
                    {"kind": "polar", "count": "bolt_count", "diameter": "bolt_circle_diameter"},
                    fastener="M5",
                ),
                {
                    "kind": "chamfer",
                    "id": "top_chamfer",
                    "name": "Top chamfer",
                    "edges": {"normal": "+z", "extreme": "max"},
                    "length": "edge_chamfer",
                },
            ],
        ),
    ),
    (
        "Angle bracket from 5 mm steel, legs 50 mm and 40 mm, 30 mm wide, one M8 hole in the middle of each leg.",
        _design(
            "Angle bracket",
            [
                _p("base_leg", 50, "mm", "horizontal leg length", "legs 50 mm"),
                _p("upright_leg", 40, "mm", "vertical leg height", "and 40 mm"),
                _p("width", 30, "mm", "bracket width", "30 mm wide"),
                _p("thickness", 5, "mm", "plate thickness", "5 mm steel"),
            ],
            [
                {
                    "id": "profile",
                    "plane": {"ref": "XZ"},
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
                {"kind": "extrude", "id": "body", "name": "L profile", "sketch": "profile", "extent": "symmetric", "distance": "width"},
                _hole("base_hole", "Base leg hole", "XY", _at(("thickness + (base_leg - thickness) / 2", 0)), fastener="M8"),
                _hole(
                    "upright_hole", "Upright leg hole", "body.left", _at((0, "thickness + (upright_leg - thickness) / 2")), fastener="M8"
                ),
            ],
        ),
    ),
    (
        "Open-top tray, outside 80 x 50 x 20 mm, 2 mm walls, 3 mm radius on the vertical corners.",
        _design(
            "Open-top tray",
            [
                _p("length", 80, "mm", "outside length", "80 x 50 x 20 mm"),
                _p("width", 50, "mm", "outside width", "80 x 50 x 20 mm"),
                _p("height", 20, "mm", "outside height", "80 x 50 x 20 mm"),
                _p("wall", 2, "mm", "wall and floor thickness", "2 mm walls"),
                _p("corner_radius", 3, "mm", "vertical corner radius", "3 mm radius"),
            ],
            [{"id": "outline", "plane": {"ref": "XY"}, "entities": [{"kind": "rect", "width": "length", "height": "width"}]}],
            [
                {"kind": "extrude", "id": "block", "name": "Outer block", "sketch": "outline", "distance": "height"},
                {"kind": "fillet", "id": "corners", "name": "Corner radius", "edges": {"parallel": "z"}, "radius": "corner_radius"},
                {"kind": "shell", "id": "hollow", "name": "Shell", "thickness": "wall", "open": [{"normal": "+z", "extreme": "max"}]},
            ],
        ),
    ),
    (
        "Flanged bushing: 20 mm bore, 30 mm outside diameter, 25 mm long overall, 45 mm flange 5 mm thick.",
        _design(
            "Flanged bushing",
            [
                _p("bore_diameter", 20, "mm", "bore", "20 mm bore"),
                _p("outer_diameter", 30, "mm", "shank diameter", "30 mm outside diameter"),
                _p("length", 25, "mm", "overall length", "25 mm long overall"),
                _p("flange_diameter", 45, "mm", "flange diameter", "45 mm flange"),
                _p("flange_thickness", 5, "mm", "flange thickness", "5 mm thick"),
            ],
            [
                {
                    "id": "half_section",
                    "plane": {"ref": "XZ"},
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
    ),
    (
        "Valve block 60 x 40 x 30 mm. M8 tapped port 20 mm deep in the top face, a 6 mm passage from the front face that meets it 10 mm below the top, two M5 counterbored mounting holes through the block 22 mm either side of centre, 1 mm chamfer on the top edges.",
        _design(
            "Valve block",
            [
                _p("length", 60, "mm", "block length", "60 x 40 x 30 mm"),
                _p("width", 40, "mm", "block width", "60 x 40 x 30 mm"),
                _p("height", 30, "mm", "block height", "60 x 40 x 30 mm"),
                _p("port_depth", 20, "mm", "tapped port depth", "20 mm deep"),
                _p("passage_diameter", 6, "mm", "cross passage", "6 mm passage"),
                _p("passage_drop", 10, "mm", "passage below the top face", "10 mm below the top"),
                _p("mount_offset", 22, "mm", "mounting holes from centre", "22 mm either side"),
                _p("edge_chamfer", 1, "mm", "top edge chamfer", "1 mm chamfer"),
            ],
            [{"id": "outline", "plane": {"ref": "XY"}, "entities": [{"kind": "rect", "width": "length", "height": "width"}]}],
            [
                {"kind": "extrude", "id": "block", "name": "Block", "sketch": "outline", "distance": "height"},
                _hole(
                    "port",
                    "M8 port",
                    "block.top",
                    _at((0, 0)),
                    type="tapped",
                    fastener="M8",
                    thread="M8x1.25",
                    depth="port_depth",
                    drill_point="118",
                ),
                _hole(
                    "passage",
                    "Cross passage",
                    "block.front",
                    _at((0, "height - passage_drop")),
                    diameter="passage_diameter",
                    depth="width / 2",
                ),
                _hole(
                    "mounts",
                    "Mounting holes",
                    "block.top",
                    _at(("-mount_offset", 0), ("mount_offset", 0)),
                    type="counterbore",
                    fastener="M5",
                ),
                {
                    "kind": "chamfer",
                    "id": "top_chamfer",
                    "name": "Top chamfer",
                    "edges": {"normal": "+z", "extreme": "max"},
                    "length": "edge_chamfer",
                },
            ],
        ),
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


def design_messages(request: str, reference: Sequence[str] = (), project: str = "", few_shot: bool = True) -> list[tuple[str, str]]:
    shots = [m for req, design in EXAMPLES for m in (("user", req), ("assistant", json.dumps(design)))] if few_shot else []
    task = _with_reference(request, reference) + (f"\n\n{project}" if project else "")
    return [("system", DESIGN_RULES), *shots, ("user", task)]


def _with_reference(request: str, reference: Sequence[str]) -> str:
    if not reference:
        return request
    return request + "\n\nReference data:\n" + "\n".join(f"- {r}" for r in reference)


def requirement_messages(request: str) -> list[tuple[str, str]]:
    example, answer = REQUIREMENT_EXAMPLE
    return [("system", REQUIREMENT_RULES), ("user", example), ("assistant", json.dumps(answer)), ("user", request)]


MAX_QUOTE = 12000


def repair_message(previous: str, problems: list[str], unchanged: bool) -> str:
    listed = "\n".join(f"- {p}" for p in problems)
    again = "This design was already returned once with the same problems; change the parts that cause them.\n" if unchanged else ""
    if not _is_json(previous) or len(previous) > MAX_QUOTE:
        reason = "was cut off before it was complete JSON" if not _is_json(previous) else f"was {len(previous)} characters long"
        return (
            f"The first attempt {reason}. Write a shorter, complete design as JSON: use patterns for repeated features, "
            "one hole feature per group of identical holes, and only the features the request asks for."
        )
    return (
        f"A first attempt at this design:\n{previous}\n\n{again}It has these problems:\n{listed}\n"
        "Write the complete corrected design as JSON. Keep everything that was right."
    )


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
    except ValueError:
        return False
    return True


def refine_message(design_json: str, instruction: str) -> str:
    return (
        f"Current design:\n{design_json}\n\nChange request: {instruction}\n\n"
        'If the change only needs new parameter values, answer {"updates": [{"name": ..., "value": ...}], "design": null}. '
        'Otherwise answer {"updates": [], "design": <the complete new design>}. Keep every parameter and feature the request does not mention.'
    )
