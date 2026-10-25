from collections.abc import Callable
from typing import Any

from build123d import Shape, Vector

from partwright_geometry import probes
from partwright_geometry.models import Finding, Location, PartMetrics, Vec
from partwright_ir import Rule, RuleKind, RuleSet

TOL = 1e-6
Check = Callable[[Shape[Any], PartMetrics, Rule], list[Finding]]


def dfm_findings(shape: Shape[Any], part: PartMetrics, rules: RuleSet) -> list[Finding]:
    return [f for rule in rules.rules for f in _check(shape, part, rule)]


def _check(shape: Shape[Any], part: PartMetrics, rule: Rule) -> list[Finding]:
    try:
        return CHECKS[rule.kind](shape, part, rule)
    except Exception as e:
        msg = f"{rule.kind} check could not run on this geometry: {type(e).__name__}: {e}"
        return [Finding(rule_id=rule.id, severity="warning", binding=rule.binding, message=msg, part=part.id)]


def hole_edge(shape: Shape[Any], part: PartMetrics, rule: Rule) -> list[Finding]:
    out = []
    for h in part.holes:
        dist, need = probes.edge_distance(shape, h), rule.value * h.diameter
        if dist is None or dist >= need - TOL:
            continue
        msg = f"Ø{_n(h.diameter)} hole centre is {_n(dist)} mm from the outer edge; needs ≥ {_n(need)} mm ({_n(rule.value)} times Ø)"
        fix = f"move the hole centre to ≥ {_n(need)} mm from the edge, or reduce Ø to ≤ {_n(dist / rule.value)} mm"
        out.append(_finding(rule, part, msg, fix, dist, need, h.center, f"Ø{_n(h.diameter)} hole"))
    return out


def wall(shape: Shape[Any], part: PartMetrics, rule: Rule) -> list[Finding]:
    thin = probes.thinnest(shape)
    if thin is None or thin[0] >= rule.value - TOL:
        return []
    t, point, face = thin
    fix = f"thicken the wall here to ≥ {_n(rule.value)} mm (raise the shell or extrude thickness)"
    return [_finding(rule, part, f"wall is {_n(t)} mm thick; needs ≥ {_n(rule.value)} mm", fix, t, rule.value, _t(point), face)]


def hole_diameter(shape: Shape[Any], part: PartMetrics, rule: Rule) -> list[Finding]:
    v = _n(rule.value)
    fix = f"enlarge the hole to Ø ≥ {v} mm or remove it"
    return [
        _finding(rule, part, f"hole Ø{_n(h.diameter)} mm is below the minimum Ø{v} mm", fix, h.diameter, rule.value, h.center, "hole")
        for h in part.holes
        if h.diameter < rule.value - TOL
    ]


def overall_size(shape: Shape[Any], part: PartMetrics, rule: Rule) -> list[Finding]:
    size = max(part.bbox_size)
    if size <= rule.value + TOL:
        return []
    axis = "XYZ"[part.bbox_size.index(size)]
    centre = Vector(*part.bbox_min) + Vector(*part.bbox_size) / 2
    msg = f"{axis} extent is {_n(size)} mm; the process allows ≤ {_n(rule.value)} mm"
    fix = f"reduce the {axis} extent to ≤ {_n(rule.value)} mm or split the part"
    return [_finding(rule, part, msg, fix, size, rule.value, _t(centre), "bounding box")]


def corner_radius(shape: Shape[Any], part: PartMetrics, rule: Rule) -> list[Finding]:
    out = []
    for r, point, where in probes.internal_corners(shape):
        if r >= rule.value - TOL:
            continue
        msg = f"internal corner radius {_n(r)} mm along the tool axis Z; a 3-axis end mill needs ≥ {_n(rule.value)} mm"
        fix = f"fillet the vertical internal edges (parallel_z) with radius ≥ {_n(rule.value)} mm"
        out.append(_finding(rule, part, msg, fix, r, rule.value, _t(point), where))
    return out


def overhang(shape: Shape[Any], part: PartMetrics, rule: Rule) -> list[Finding]:
    out = []
    for angle, point, face in probes.overhangs(shape):
        if angle <= rule.value + 1e-3:
            continue
        msg = f"downward face overhangs {_n(angle)}° from vertical (build direction +Z); FDM allows ≤ {_n(rule.value)}°"
        fix = f"chamfer the underside to ≤ {_n(rule.value)}° from vertical, add supports, or reorient the part"
        out.append(_finding(rule, part, msg, fix, angle, rule.value, _t(point), face))
    return out


CHECKS: dict[RuleKind, Check] = {
    "min_hole_edge_ratio": hole_edge,
    "min_wall_thickness": wall,
    "min_hole_diameter": hole_diameter,
    "max_overall_size": overall_size,
    "min_internal_corner_radius": corner_radius,
    "max_overhang_angle": overhang,
}


def _finding(rule: Rule, part: PartMetrics, msg: str, fix: str, measured: float, required: float, point: Vec, face: str) -> Finding:
    return Finding(
        rule_id=rule.id,
        severity=rule.severity if rule.binding == "static" else "warning",
        binding=rule.binding,
        message=msg,
        part=part.id,
        measured=measured,
        required=required,
        location=Location(point=point, face=face),
        suggestion=fix,
    )


def _n(v: float) -> str:
    return f"{round(v, 2):g}"


def _t(v: Vector) -> Vec:
    return (v.X, v.Y, v.Z)
