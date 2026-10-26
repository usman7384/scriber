from pathlib import Path

from partwright_agent import check
from partwright_geometry import BuildError, LocalGeometry
from partwright_training.spec import Spec


def failures(spec: Spec, geometry: LocalGeometry, out_dir: Path) -> list[str]:
    try:
        artifact = geometry.build(spec.design, out_dir)
    except BuildError as e:
        return [f"build {e.kind}: {str(e)[:200]}"]
    problems = [f"finding {f.rule_id}: {f.message}" for f in artifact.findings if f.severity == "error"]
    problems += [
        f"check {c.requirement.kind} {c.requirement.description}: {c.actual}" for c in check(list(spec.checks), artifact) if not c.passed
    ]
    return problems
