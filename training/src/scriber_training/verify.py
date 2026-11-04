import math
from pathlib import Path

from scriber_agent import Requirement, check
from scriber_geometry import Artifact, BuildError, LocalGeometry
from scriber_ir import Design
from scriber_training.context import RULES
from scriber_training.spec import Position, Spec

PLACED_MM = 0.05


def failures(spec: Spec, geometry: LocalGeometry, out_dir: Path) -> list[str]:
    return design_failures(spec.design, spec.checks, spec.exempt, geometry, out_dir, spec.positions)


def design_failures(
    design: Design,
    checks: tuple[Requirement, ...],
    exempt: tuple[str, ...],
    geometry: LocalGeometry,
    out_dir: Path,
    positions: tuple[Position, ...] = (),
) -> list[str]:
    try:
        artifact = geometry.build(design, out_dir, RULES)
    except BuildError as e:
        return [f"build {e.kind}: {str(e)[:200]}"]
    problems = [f"finding {f.rule_id}: {f.message}" for f in artifact.findings if f.severity == "error" and f.rule_id not in exempt]
    unmet = [c for c in check(list(checks), artifact) if not c.passed]
    problems += [f"check {c.requirement.kind} {c.requirement.description}: {c.actual}" for c in unmet]
    return problems + misplaced(artifact, positions)


def misplaced(artifact: Artifact, positions: tuple[Position, ...]) -> list[str]:
    x0, y0 = (min(p.bbox_min[i] for p in artifact.parts) for i in range(2))
    holes = [(h.center[0] - x0, h.center[1] - y0, h.diameter) for p in artifact.parts for h in p.holes]
    return [
        f"position no {d:g} mm hole at ({x:g}, {y:g}) from the corner"
        for x, y, d in positions
        if not any(abs(hd - d) <= PLACED_MM and math.dist((hx, hy), (x, y)) <= PLACED_MM for hx, hy, hd in holes)
    ]
