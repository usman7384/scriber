from pathlib import Path

from partwright_agent import Requirement, check
from partwright_geometry import BuildError, LocalGeometry
from partwright_ir import Design
from partwright_training.context import RULES
from partwright_training.spec import Spec


def failures(spec: Spec, geometry: LocalGeometry, out_dir: Path) -> list[str]:
    return design_failures(spec.design, spec.checks, spec.exempt, geometry, out_dir)


def design_failures(
    design: Design, checks: tuple[Requirement, ...], exempt: tuple[str, ...], geometry: LocalGeometry, out_dir: Path
) -> list[str]:
    try:
        artifact = geometry.build(design, out_dir, RULES)
    except BuildError as e:
        return [f"build {e.kind}: {str(e)[:200]}"]
    problems = [f"finding {f.rule_id}: {f.message}" for f in artifact.findings if f.severity == "error" and f.rule_id not in exempt]
    unmet = [c for c in check(list(checks), artifact) if not c.passed]
    problems += [f"check {c.requirement.kind} {c.requirement.description}: {c.actual}" for c in unmet]
    return problems
