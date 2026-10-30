# Builds the web e2e fixtures with the real geometry service, FreeCAD and PrusaSlicer: uv run python apps/web/e2e/fixtures/make_fixtures.py

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from partwright_api.structure import structure
from partwright_evals.tools import FREECAD, PRUSASLICER, missing, tool
from partwright_geometry import LocalGeometry, UnsupportedExportError, export_fcstd, fcstd_plan, slice_stl
from partwright_ir import Design, label

HERE = Path(__file__).parent


def plate(thickness: float) -> dict[str, Any]:
    return {
        "title": "Base plate",
        "params": [
            {"name": "length", "value": 120, "unit": "mm", "provenance": {"source": "prompt", "quote": "120 x 80 x 5 mm"}},
            {"name": "width", "value": 80, "unit": "mm", "provenance": {"source": "prompt", "quote": "120 x 80 x 5 mm"}},
            {"name": "thickness", "value": thickness, "unit": "mm", "min": 2, "max": 20},
            {"name": "hole_d", "value": 6.6, "unit": "mm", "provenance": {"source": "standard", "ref": "ISO 273"}},
        ],
        "parts": [
            {
                "id": "plate",
                "name": "Plate",
                "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "length", "height": "width"}]}],
                "features": [
                    {"kind": "extrude", "id": "body", "name": "Plate", "sketch": "s", "distance": "thickness"},
                    {
                        "kind": "hole",
                        "id": "holes",
                        "name": "Bolt holes",
                        "plane": {"offset": "thickness"},
                        "at": {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": 85, "spacing_y": 50},
                        "diameter": "hole_d",
                    },
                ],
            }
        ],
    }


def block(pid: str, size: float) -> dict[str, Any]:
    return {
        "id": pid,
        "name": pid.title(),
        "material": "PLA",
        "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": size, "height": size}]}],
        "features": [{"kind": "extrude", "id": "body", "name": "Body", "sketch": "s", "distance": size}],
    }


STACK = {
    "title": "Stack",
    "params": [],
    "parts": [block("plate", 40), block("cube", 10)],
    "assembly": {
        "connectors": [{"id": "seat", "part": "plate", "origin": [0, 0, 40]}, {"id": "foot", "part": "cube"}],
        "joints": [{"id": "cube_on_plate", "parent": "seat", "child": "foot"}],
    },
}

MOTOR_HOLDER = {
    "title": "Motor holder",
    "params": [
        {"name": "motor_d", "value": 28, "unit": "mm", "provenance": {"source": "prompt", "quote": "28 mm motor"}},
        {"name": "clearance", "value": 0.3, "unit": "mm"},
        {"name": "wall", "value": 3, "unit": "mm"},
        {"name": "ring_h", "value": 20, "unit": "mm"},
        {"name": "base_l", "value": 60, "unit": "mm"},
        {"name": "base_w", "value": 40, "unit": "mm"},
        {"name": "base_t", "value": 4, "unit": "mm"},
        {"name": "screw_spacing", "value": 48, "unit": "mm"},
    ],
    "parts": [
        {
            "id": "holder",
            "name": "Motor holder",
            "material": "PLA",
            "process": "fdm",
            "sketches": [
                {"id": "base", "entities": [{"kind": "rect", "width": "base_l", "height": "base_w"}]},
                {
                    "id": "ring",
                    "plane": {"offset": "base_t"},
                    "entities": [
                        {"kind": "circle", "diameter": "motor_d + 2 * clearance + 2 * wall"},
                        {"kind": "circle", "diameter": "motor_d + 2 * clearance", "subtract": True},
                    ],
                },
            ],
            "features": [
                {"kind": "extrude", "id": "base", "name": "Base", "sketch": "base", "distance": "base_t"},
                {"kind": "extrude", "id": "ring", "name": "Ring", "sketch": "ring", "distance": "ring_h"},
                {
                    "kind": "hole",
                    "id": "screws",
                    "name": "M3 screw holes",
                    "plane": {"offset": "base_t"},
                    "at": {"kind": "points", "points": [["-screw_spacing / 2", 0], ["screw_spacing / 2", 0]]},
                    "fastener": "M3",
                },
            ],
        }
    ],
}


def build(geometry: LocalGeometry, name: str, data: dict[str, Any], stl: bool = False) -> None:
    design = Design.model_validate(data)
    with tempfile.TemporaryDirectory() as tmp:
        art = geometry.build(design, Path(tmp))
        shutil.copy(art.files["glb"], HERE / f"{name}.glb")
        if stl:
            shutil.copy(art.files["stl"], HERE / f"{name}.stl")
        geometry.thumbnail(art.files["glb"], HERE / f"{name}.png")
    lo = [min(p.bbox_min[i] for p in art.parts) for i in range(3)]
    hi = [max(p.bbox_min[i] + p.bbox_size[i] for p in art.parts) for i in range(3)]
    meta = {
        "title": design.title,
        "params": [p.model_dump() | {"label": label(p.name)} for p in design.params],
        "metrics": {
            "bbox": [round(h - lo_, 6) for h, lo_ in zip(hi, lo, strict=True)],
            "volume": round(sum(p.volume for p in art.parts), 3),
            "mass_g": None,
            "holes": sum(len(p.holes) for p in art.parts),
        },
        "findings": [f.model_dump(mode="json") for f in art.findings],
        "structure": structure(design, geometry.structure(design)).model_dump(mode="json")["parts"],
    }
    (HERE / f"{name}.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def external_tools(geometry: LocalGeometry) -> None:
    freecad, slicer = tool(FREECAD), tool(PRUSASLICER)
    if freecad is None or slicer is None:
        raise SystemExit(missing(FREECAD if freecad is None else PRUSASLICER))
    base = Design.model_validate(plate(5))
    export_fcstd(base, geometry.frames(base), freecad, HERE / "base-plate-t5.FCStd")
    try:
        fcstd_plan(Design.model_validate(STACK), [])
        raise SystemExit("the stack assembly unexpectedly maps to FreeCAD")
    except UnsupportedExportError as e:
        unsupported = str(e)
    with tempfile.TemporaryDirectory() as tmp:
        sliced = slice_stl(slicer, HERE / "motor-holder.stl", Path(tmp) / "motor-holder.gcode")
    found = {"stack_fcstd_error": unsupported, "motor_holder_slice": sliced.model_dump()}
    (HERE / "external-tools.json").write_text(json.dumps(found, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    geometry = LocalGeometry()
    try:
        build(geometry, "base-plate-t5", plate(5))
        build(geometry, "base-plate-t7", plate(7))
        build(geometry, "stack", STACK)
        build(geometry, "motor-holder", MOTOR_HOLDER, stl=True)
        external_tools(geometry)
    finally:
        geometry.close()


if __name__ == "__main__":
    main()
