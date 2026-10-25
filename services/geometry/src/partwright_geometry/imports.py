from collections import Counter
from pathlib import Path
from typing import Any

import trimesh
from build123d import Shape, import_step

from partwright_geometry.metrics import holes, part_metrics
from partwright_geometry.models import MESH_SUFFIXES, PartMetrics
from partwright_ir import ShapeDescriptor


def describe(path: Path) -> ShapeDescriptor:
    if path.suffix.lower() in MESH_SUFFIXES:
        return _describe_mesh(path)
    shape = import_step(path)
    a, b, c = sorted(shape.bounding_box().size)
    return ShapeDescriptor(
        bbox_sorted=(a, b, c),
        volume=shape.volume,
        area=shape.area,
        hole_diameters=[h.diameter for h in holes(shape)],
        face_kinds=dict(Counter(f.geom_type.name.lower() for f in shape.faces())),
    )


def step_parts(path: Path) -> list[PartMetrics]:
    return [part_metrics(f"part_{i}", s) for i, s in enumerate(_leaves(import_step(path)))]


def _describe_mesh(path: Path) -> ShapeDescriptor:
    mesh = trimesh.load_mesh(path)
    a, b, c = sorted(float(x) for x in mesh.extents)
    volume = abs(float(mesh.volume)) if mesh.is_watertight else 0.0
    return ShapeDescriptor(bbox_sorted=(a, b, c), volume=volume, area=float(mesh.area), face_kinds={"triangle": len(mesh.faces)})


def _leaves(shape: Shape[Any]) -> list[Shape[Any]]:
    return [leaf for c in shape.children for leaf in _leaves(c)] if shape.children else [shape]
