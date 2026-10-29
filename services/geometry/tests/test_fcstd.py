import os
from pathlib import Path
from typing import Any

import pytest

from partwright_geometry import LocalGeometry, UnsupportedExportError, export_fcstd, fcstd_plan, inspect_fcstd
from partwright_geometry.fcstd import _endpoint_tangents, _expr
from partwright_geometry.models import Constraint, SketchFrame
from partwright_ir import Design, apply_params

FREECAD = os.environ.get("PARTWRIGHT_FREECAD")
needs_freecad = pytest.mark.skipif(not FREECAD, reason="PARTWRIGHT_FREECAD is unset")
XY = SketchFrame(ref="XY", origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 0, 1), out=0)
PARAMS = [
    {"name": "t", "value": 6, "unit": "mm"},
    {"name": "w", "value": 40, "unit": "mm"},
    {"name": "tilt", "value": 30, "unit": "deg"},
    {"name": "pcd", "value": 24, "unit": "mm"},
]
SLOT = {"kind": "slot", "center": [0, 22], "length": 20, "width": 6, "angle": "tilt"}
PATH = {
    "kind": "path",
    "start": [-30, -28],
    "segments": [{"to": [-14, -28]}, {"to": [-14, -14], "fillet": 3}, {"to": [-30, -14]}],
}


def kitchen_sink() -> Design:
    sketches = [
        {"id": "base", "entities": [{"kind": "rect", "width": 70, "height": "w + 20", "corner_radius": 5}]},
        {"id": "boss", "plane": {"ref": "base.end"}, "entities": [{"kind": "circle", "center": [20, 0], "diameter": 16}]},
        {"id": "slot", "plane": {"ref": "base.top"}, "entities": [SLOT]},
        {"id": "notch", "plane": {"ref": "base.end"}, "entities": [PATH]},
        {"id": "rib", "plane": {"ref": "XZ"}, "entities": [{"kind": "polygon", "points": [[-30, 6], [-20, 6], [-30, 16]]}]},
        {"id": "side", "plane": {"ref": "YZ", "offset": 35}, "entities": [{"kind": "rect", "center": [0, 3], "width": 10, "height": 3}]},
        {"id": "tilted", "plane": {"ref": "lean"}, "entities": [{"kind": "circle", "center": [20, 0], "diameter": 4}]},
        {"id": "fin", "entities": [{"kind": "polygon", "points": [[0, -20], [10, -20], [0, -26]]}]},
        {"id": "cap", "plane": {"ref": "fin.end"}, "entities": [{"kind": "circle", "center": [3, -22], "diameter": 2}]},
    ]
    features = [
        {"kind": "extrude", "id": "base", "name": "Base", "sketch": "base", "distance": "t"},
        {"kind": "extrude", "id": "boss", "name": "Boss", "sketch": "boss", "extent": "two_sided", "distance": 8, "distance2": 2},
        {"kind": "extrude", "id": "slot", "name": "Slot", "sketch": "slot", "mode": "cut", "distance": "t / 2"},
        {"kind": "extrude", "id": "notch", "name": "Notch", "sketch": "notch", "mode": "cut", "extent": "through_all"},
        {"kind": "extrude", "id": "rib", "name": "Rib", "sketch": "rib", "extent": "symmetric", "distance": 4},
        {"kind": "extrude", "id": "side", "name": "Side groove", "sketch": "side", "mode": "cut", "extent": "symmetric", "distance": 4},
        {"kind": "extrude", "id": "tilted", "name": "Tilted pin bore", "sketch": "tilted", "mode": "cut", "extent": "through_all"},
        {"kind": "extrude", "id": "fin", "name": "Clockwise fin", "sketch": "fin", "distance": "t - 1"},
        {"kind": "extrude", "id": "cap", "name": "Cap recess", "sketch": "cap", "mode": "cut", "distance": 2},
        {
            "kind": "hole",
            "id": "ring",
            "name": "Ring holes",
            "plane": {"ref": "base.start"},
            "at": {"kind": "polar", "center": [20, 0], "count": 4, "diameter": "pcd", "start_angle": 45},
            "diameter": 3,
            "depth": 4,
        },
        {
            "kind": "hole",
            "id": "grid",
            "name": "Grid holes",
            "plane": {"ref": "base.end"},
            "at": {"kind": "grid", "center": [-15, 15], "count_x": 2, "count_y": 2, "spacing_x": 8, "spacing_y": 6},
            "fastener": "M3",
        },
    ]
    datums = [{"id": "lean", "base": "XY", "offset": 2, "rotate_about": "y", "angle": 10}]
    part = {"id": "sink", "name": "Kitchen sink", "datums": datums, "sketches": sketches, "features": features}
    return Design.model_validate({"title": "Kitchen sink", "params": PARAMS, "parts": [part]})


@needs_freecad
def test_fcstd_rebuilds_every_mapped_construct_and_follows_parameter_edits(geometry: LocalGeometry, tmp_path: Path) -> None:
    design, freecad = kitchen_sink(), Path(str(FREECAD))
    [ours] = geometry.build(design, tmp_path / "ours").parts
    edits = {"t": 7.0, "w": 44.0, "tilt": 40.0, "pcd": 22.0}
    report = inspect_fcstd(
        freecad, export_fcstd(design, geometry.frames(design), freecad, tmp_path / "sink.FCStd"), edits, tmp_path / "edits"
    )
    [body] = report.bodies
    sketches = [f for f in body.features if f.type == "Sketcher::SketchObject"]
    assert report.errors == [] and body.valid and body.solids == 1
    assert [f.label for f in body.features if f.type != "Sketcher::SketchObject"] == [f.name for f in design.parts[0].features]
    assert all(s.dof == 0 and s.redundant == 0 and s.conflicting == 0 for s in sketches)
    assert abs(body.volume / ours.volume - 1) < 1e-9
    for name, value in edits.items():
        [edited] = geometry.import_step(report.edited[name])
        [expected] = geometry.measure(apply_params(design, {name: value}))
        assert abs(edited.volume / expected.volume - 1) < 1e-9, name
        assert edited.center_of_mass and expected.center_of_mass
        assert max(abs(a - b) for a, b in zip(edited.center_of_mass, expected.center_of_mass, strict=True)) < 1e-6, name


def test_tangent_and_coincidence_at_a_point_merge_into_one_endpoint_tangency() -> None:
    constraints = [
        Constraint(kind="coincident", refs=["g0.end", "g1.start"]),
        Constraint(kind="tangent", refs=["g0", "g1", "g1.start"]),
        Constraint(kind="coincident", refs=["g1.end", "g2.start"]),
    ]
    assert _endpoint_tangents(constraints) == [
        Constraint(kind="tangent", refs=["g0.end", "g1.start"]),
        Constraint(kind="coincident", refs=["g1.end", "g2.start"]),
    ]


def test_ir_expressions_become_spreadsheet_expressions() -> None:
    assert _expr("plate_length - 2 * w", "distance") == "(Parameters.plate_length - (2.0 * Parameters.w_))"
    assert _expr("(0) + (pcd) / 2 * cos((45) + 90.0)", "distance") == "(0.0 + ((Parameters.pcd_ / 2.0) * cos((45.0 + 90.0))))"
    assert _expr("tilt * t", "angle") == "(Parameters.tilt_ * Parameters.t_) * 1 deg"
    assert _expr("40.0", "distance") is None
    assert _expr("max(w, 3)", "distance") is None


@pytest.mark.parametrize(
    ("feature", "match"),
    [
        ({"kind": "revolve", "id": "r", "name": "R", "sketch": "s"}, "revolve feature 'r'"),
        ({"kind": "fillet", "id": "f", "name": "F", "edges": {}, "radius": 1}, "fillet feature 'f'"),
        ({"kind": "extrude", "id": "e", "name": "E", "sketch": "s", "mode": "intersect", "distance": 2}, "intersect"),
        (
            {
                "kind": "hole",
                "id": "h",
                "name": "H",
                "plane": {},
                "at": {"kind": "points", "points": [[0, 0]]},
                "type": "counterbore",
                "fastener": "M3",
            },
            "counterbores",
        ),
    ],
)
def test_constructs_without_a_freecad_mapping_raise(feature: dict[str, Any], match: str) -> None:
    pad = {"kind": "extrude", "id": "pad", "name": "Pad", "sketch": "s", "distance": 5}
    part = {
        "id": "p",
        "name": "P",
        "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": 20, "height": 20}]}],
        "features": [pad, feature],
    }
    design = Design.model_validate({"title": "P", "params": [], "parts": [part]})
    with pytest.raises(UnsupportedExportError, match=match):
        fcstd_plan(design, [XY, XY])
