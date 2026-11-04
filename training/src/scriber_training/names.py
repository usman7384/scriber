import random
import re
from dataclasses import replace
from typing import Any

from scriber_ir import Design
from scriber_training.spec import Spec

SYNONYMS = {
    "length": ("overall_length", "part_length", "size_x"),
    "plate_length": ("length", "overall_length", "plate_x"),
    "plate_width": ("width", "overall_width", "plate_y"),
    "width": ("overall_width", "part_width", "size_y"),
    "height": ("overall_height", "part_height", "size_z"),
    "thickness": ("plate_thickness", "material_thickness", "thk"),
    "hole_margin": ("edge_margin", "hole_inset", "edge_distance"),
    "mount_margin": ("mount_inset", "mount_edge_distance"),
    "hole_pitch": ("hole_spacing", "pitch"),
    "hole_count": ("num_holes", "n_holes"),
    "bolt_count": ("num_bolts", "n_bolts"),
    "bolt_circle_diameter": ("pcd", "bcd", "pitch_circle_diameter"),
    "bore_diameter": ("bore", "centre_bore", "bore_d"),
    "corner_radius": ("corner_r", "outline_radius"),
    "edge_chamfer": ("chamfer", "top_chamfer"),
    "wall": ("wall_thickness", "wall_t"),
    "outer_diameter": ("od", "outside_diameter"),
    "hole_diameter": ("hole_d", "hole_dia"),
    "base_leg": ("leg_a", "horizontal_leg"),
    "upright_leg": ("leg_b", "vertical_leg"),
}
# keys whose string values are ids, enums or text, never expressions
NOT_EXPRESSIONS = frozenset(
    {"id", "name", "intent", "kind", "sketch", "ref", "of", "features", "type", "direction", "axis", "mode", "extent", "fastener"}
    | {"thread", "fit", "drill_point", "mirror_plane", "normal", "parallel", "convexity", "extreme", "provenance", "arc"}
)
IDENT = re.compile(r"\b[a-z_][a-z0-9_]*\b")


def renamed(spec: Spec, rng: random.Random, rate: float = 0.4) -> Spec:
    names = {p.name for p in spec.design.params}
    mapping: dict[str, str] = {}
    for name in sorted(names):
        options = [s for s in SYNONYMS.get(name, ()) if s not in names and s not in mapping.values()]
        if options and rng.random() < rate:
            mapping[name] = rng.choice(options)
    if not mapping:
        return spec
    data = spec.design.model_dump(mode="json")
    for p in data["params"]:
        p["name"] = mapping.get(p["name"], p["name"])
    for part in data["parts"]:
        part["sketches"] = [_swap(s, mapping) for s in part["sketches"]]
        part["features"] = [_swap(f, mapping) for f in part["features"]]
    for c in (data.get("assembly") or {}).get("connectors", []):
        c["origin"] = _swap(c["origin"], mapping)
    for j in (data.get("assembly") or {}).get("joints", []):
        j["angle"], j["offset"] = _swap(j["angle"], mapping), _swap(j["offset"], mapping)
    return replace(spec, design=Design.model_validate(data))


def _swap(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {k: v if k in NOT_EXPRESSIONS else _swap(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_swap(v, mapping) for v in value]
    if isinstance(value, str):
        return IDENT.sub(lambda m: mapping.get(m.group(0), m.group(0)), value)
    return value
