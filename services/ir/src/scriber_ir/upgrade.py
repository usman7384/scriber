from typing import Any

EDGE_PRESETS: dict[str, dict[str, str]] = {
    "all": {},
    "top": {"normal": "+z", "extreme": "max"},
    "bottom": {"normal": "-z", "extreme": "max"},
    "parallel_x": {"parallel": "x"},
    "parallel_y": {"parallel": "y"},
    "parallel_z": {"parallel": "z"},
}
OPEN_FACE = {"top": [{"normal": "+z", "extreme": "max"}], "bottom": [{"normal": "-z", "extreme": "max"}], "none": []}


def upgrade_v1(data: dict[str, Any]) -> dict[str, Any]:
    parts = [_part(p) if isinstance(p, dict) else p for p in data.get("parts", [])]
    return {**data, "ir_version": 2, "parts": parts}


def _part(part: dict[str, Any]) -> dict[str, Any]:
    sketches = [{**s, "plane": _plane(s["plane"])} if isinstance(s, dict) and "plane" in s else s for s in part.get("sketches", [])]
    return {**part, "sketches": sketches, "features": [_feature(f) if isinstance(f, dict) else f for f in part.get("features", [])]}


def _plane(plane: Any) -> Any:
    if not isinstance(plane, dict) or "ref" in plane:
        return plane
    return {"ref": plane.get("base", "XY"), **({"offset": plane["offset"]} if "offset" in plane else {})}


def _feature(f: dict[str, Any]) -> dict[str, Any]:
    out = dict(f)
    if "plane" in out:
        out["plane"] = _plane(out["plane"])
    if out.get("kind") == "extrude" and "symmetric" in out:
        out["extent"] = "symmetric" if out.pop("symmetric") else out.get("extent", "blind")
    if out.get("kind") == "hole" and ("counterbore_diameter" in out or "counterbore_depth" in out):
        cbd, cbdepth = out.pop("counterbore_diameter", None), out.pop("counterbore_depth", None)
        if cbd is not None or cbdepth is not None:
            out.update(type="counterbore", cb_diameter=cbd, cb_depth=cbdepth)
    if out.get("kind") in ("fillet", "chamfer") and isinstance(out.get("edges"), str):
        out["edges"] = EDGE_PRESETS.get(out["edges"], {})
    if out.get("kind") == "shell" and "open_face" in out:
        out["open"] = OPEN_FACE.get(out.pop("open_face"), [])
    return out
