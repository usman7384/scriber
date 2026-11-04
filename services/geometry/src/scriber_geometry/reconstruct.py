from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import trimesh

from scriber_geometry.fits import Circle2, grid, polar
from scriber_geometry.mesh_sections import Points
from scriber_geometry.stack import Body, Opening, Profile, Stack, analyse
from scriber_ir import Design

PATTERN_TOL = 0.05
Hole = tuple[Opening, Circle2]


def reconstruct_mesh(path: Path) -> Design:
    mesh = trimesh.load_mesh(path, force="mesh")
    mesh.merge_vertices(digits_vertex=4)
    mesh.update_faces(mesh.nondegenerate_faces())
    return to_design(analyse(mesh), path.name)


def to_design(stack: Stack, source: str) -> Design:
    ir = _Ir(source)
    level = _levels(stack, ir)
    top = len(stack.levels) - 1
    for i, body in enumerate(stack.bodies):
        _add(ir, body, i, level)
    holes = [(o, o.profile.circle) for o in stack.openings if o.profile.circle]
    for group in _hole_groups(holes, stack.noise):
        if len(group) == 1:
            _cut(ir, group[0][0], level, top)
        else:
            _holes(ir, group, level, top)
    for o in stack.openings:
        if not o.profile.circle:
            _cut(ir, o, level, top)
    stem = Path(source).stem
    part = {"id": "part", "name": stem.replace("_", " ").title(), "sketches": ir.sketches, "features": ir.features}
    return Design.model_validate({"title": f"Reconstructed {stem}"[:60], "params": ir.params, "parts": [part]})


class _Ir:
    def __init__(self, source: str) -> None:
        self.source = source
        self.params: list[dict[str, Any]] = []
        self.sketches: list[dict[str, Any]] = []
        self.features: list[dict[str, Any]] = []

    def param(self, name: str, value: float, note: str) -> str:
        name = _unique(name, {p["name"] for p in self.params})
        v = round(value, 3)
        prov = {"source": "mesh_fit", "ref": self.source, "quote": note}
        self.params.append({"name": name, "value": v, "unit": "mm", "min": round(v / 2, 3), "max": round(2 * v, 3), "provenance": prov})
        return name

    def feature(self, kind: str, name: str, **fields: Any) -> None:
        fid = _unique(name, {f["id"] for f in self.features})
        prov = {"source": "mesh_fit", "ref": self.source}
        self.features.append({"kind": kind, "id": fid, "name": fid.replace("_", " ").title(), "provenance": prov, **fields})


def _unique(name: str, taken: set[str]) -> str:
    n = 2
    candidate = name
    while candidate in taken:
        candidate, n = f"{name}_{n}", n + 1
    return candidate


@dataclass(frozen=True)
class _Level:
    z: float
    base: float
    names: tuple[str, ...] = ()

    @property
    def expr(self) -> str | float:
        if not self.names:
            return self.base
        return " + ".join(self.names if self.base == 0 else (f"{self.base:g}", *self.names))


def _levels(stack: Stack, ir: _Ir) -> list[_Level]:
    level = [_Level(z, round(z, 3)) for z in stack.levels]
    for i, body in enumerate(stack.bodies):
        lo = level[body.lo]
        name = ir.param("thickness" if i == 0 else f"boss_{i}_height", level[body.hi].z - lo.z, "distance between planar levels")
        level[body.hi] = _Level(level[body.hi].z, lo.base, (*lo.names, name))
    return level


def _span(level: list[_Level], lo: int, hi: int) -> str | float:
    a, b = level[lo], level[hi]
    if a.base == b.base and b.names[: len(a.names)] == a.names and len(b.names) > len(a.names):
        return " + ".join(b.names[len(a.names) :])
    return round(b.z - a.z, 3)


def _add(ir: _Ir, body: Body, i: int, level: list[_Level]) -> None:
    name = "body" if i == 0 else f"boss_{i}"
    diameter = ("outer_diameter" if i == 0 else f"{name}_diameter") if len(body.outlines) == 1 else None
    entities = [_entity(ir, p, diameter) for p in body.outlines]
    ir.sketches.append({"id": f"s_{name}", "plane": {"offset": level[body.lo].expr}, "entities": entities})
    ir.feature("extrude", name, sketch=f"s_{name}", distance=_span(level, body.lo, body.hi))


def _cut(ir: _Ir, o: Opening, level: list[_Level], top: int) -> None:
    fid = _unique("bore" if o.profile.circle else "window", {f["id"] for f in ir.features})
    extent = {"extent": "through_all"} if (o.lo, o.hi) == (0, top) else {"distance": _span(level, o.lo, o.hi)}
    ir.sketches.append({"id": f"s_{fid}", "plane": {"offset": level[o.lo].expr}, "entities": [_entity(ir, o.profile, f"{fid}_diameter")]})
    ir.feature("extrude", fid, sketch=f"s_{fid}", mode="cut", **extent)


def _entity(ir: _Ir, p: Profile, diameter: str | None) -> dict[str, Any]:
    if p.circle is None:
        return {"kind": "polygon", "points": [[round(x, 3), round(y, 3)] for x, y in p.polygon]}
    note = f"least-squares circle, rms {p.circle.rms:.4f} mm"
    d = ir.param(diameter, 2 * p.circle.r, note) if diameter else round(2 * p.circle.r, 3)
    return {"kind": "circle", "center": [round(p.circle.x, 3), round(p.circle.y, 3)], "diameter": d}


def _hole_groups(holes: list[Hole], noise: float) -> list[list[Hole]]:
    tol = PATTERN_TOL + 3 * noise
    groups: list[list[Hole]] = []
    for h in sorted(holes, key=lambda h: (h[0].lo, h[0].hi, h[1].r)):
        g = groups[-1] if groups else None
        if g and (g[0][0].lo, g[0][0].hi) == (h[0].lo, h[0].hi) and abs(g[0][1].r - h[1].r) <= tol:
            g.append(h)
        else:
            groups.append([h])
    return groups


def _holes(ir: _Ir, group: list[Hole], level: list[_Level], top: int) -> None:
    rms = max(c.rms for _, c in group)
    d = ir.param("hole_diameter", 2 * float(np.mean([c.r for _, c in group])), f"least-squares cylinders, max rms {rms:.4f} mm")
    o = group[0][0]
    depth = None if (o.lo, o.hi) == (0, top) else _span(level, o.lo, o.hi)
    at = _placement(ir, np.array([(c.x, c.y) for _, c in group]))
    ir.feature("hole", "holes", plane={"offset": level[o.hi].expr}, at=at, diameter=d, depth=depth)


def _placement(ir: _Ir, centres: Points) -> dict[str, Any]:
    if p := polar(centres, PATTERN_TOL):
        pcd = ir.param("hole_pcd", p.diameter, "circle through the hole centres")
        return {
            "kind": "polar",
            "center": [round(p.x, 3), round(p.y, 3)],
            "count": len(centres),
            "diameter": pcd,
            "start_angle": round(p.start_angle, 3),
        }
    if g := grid(centres, PATTERN_TOL):
        sx = ir.param("hole_spacing_x", g.sx, "grid of hole centres") if g.nx > 1 else 0.0
        sy = ir.param("hole_spacing_y", g.sy, "grid of hole centres") if g.ny > 1 else 0.0
        return {
            "kind": "grid",
            "center": [round(g.x, 3), round(g.y, 3)],
            "count_x": g.nx,
            "count_y": g.ny,
            "spacing_x": sx,
            "spacing_y": sy,
        }
    return {"kind": "points", "points": [[round(x, 3), round(y, 3)] for x, y in centres]}
