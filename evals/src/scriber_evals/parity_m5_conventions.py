import json
import os
import statistics
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from scriber_agent import LLM, dump_steps, generate
from scriber_cli.config import llm_for
from scriber_evals.parity import Demo, Evidence, Measured, Rig, evidence
from scriber_evals.parity_m2 import side_walls
from scriber_geometry import Artifact, HoleInfo, PartMetrics
from scriber_ir import Design, ExprError, evaluate
from scriber_ir.model import Fillet

CASES = Path(__file__).parents[2] / "cases" / "conventions.yaml"
BASE_ENV = "SCRIBER_CX13_BASE"
BASE = "qwen3.5:0.8b-q8_0"
MARGIN = 10.0
# evals/parity/m5/house-style.md
WALL, BORE, FILLET, EDGE_RATIO = 2.5, 4.0, 1.0, 2.0
TOL = 0.05
SUFFIX = {"mm": "_mm", "deg": "_deg", "": "_n"}
Convention = Literal["wall", "insert", "fillet", "edge", "names"]


class ConventionCase(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    prompt: str
    conventions: list[Convention]
    holes: int = 0


class Score(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    built: bool
    followed: dict[str, bool]
    score: float


def load_cases(path: Path) -> list[ConventionCase]:
    return [ConventionCase.model_validate(c) for c in yaml.safe_load(path.read_text(encoding="utf-8"))]


def adherence(case: ConventionCase, design: Design | None, art: Artifact | None) -> Score:
    checks: dict[Convention, Callable[[], bool]] = {
        "wall": lambda: art is not None and _walls(art),
        "insert": lambda: art is not None and _inserts(art, case.holes),
        "fillet": lambda: design is not None and _fillet(design),
        "edge": lambda: art is not None and _edges(art),
        "names": lambda: design is not None and _names(design),
    }
    followed = {c: checks[c]() for c in case.conventions}
    return Score(id=case.id, built=art is not None, followed=followed, score=round(100 * sum(followed.values()) / len(followed), 1))


def _walls(art: Artifact) -> bool:
    walls = side_walls(art.files["stl"])
    return len(walls) == 4 and all(abs(w - WALL) <= TOL for w in walls)


def _inserts(art: Artifact, count: int) -> bool:
    diameters = [h.diameter for p in art.parts for h in p.holes]
    return len(diameters) == count and all(abs(d - BORE) <= TOL for d in diameters)


def _edges(art: Artifact) -> bool:
    gaps = [(_edge_gap(p, h), h.diameter) for p in art.parts for h in p.holes if abs(h.axis[2]) > 0.99]
    return bool(gaps) and all(gap >= EDGE_RATIO * d - TOL for gap, d in gaps)


def _edge_gap(p: PartMetrics, h: HoleInfo) -> float:
    return min(min(h.center[i] - p.bbox_min[i], p.bbox_min[i] + p.bbox_size[i] - h.center[i]) for i in (0, 1))


def _fillet(design: Design) -> bool:
    values = design.param_values()
    return any(isinstance(f, Fillet) and _near(f.radius, values, FILLET) for p in design.parts for f in p.features)


def _near(expr: float | str, values: dict[str, float], target: float) -> bool:
    try:
        return abs(evaluate(expr, values) - target) <= TOL
    except ExprError:  # an unresolvable radius cannot follow the convention
        return False


def _names(design: Design) -> bool:
    return bool(design.params) and all(p.name.endswith(SUFFIX[p.unit]) for p in design.params)


def benchmark(rig: Rig, llm: LLM, label: str) -> list[Score]:
    scores = []
    for case in load_cases(CASES):
        out = rig.out / label / case.id
        steps = list(generate(case.prompt, llm, rig.geometry, out, rig.config.agent.max_repairs, rig.config.agent.seed))
        (out / "steps.json").write_text(dump_steps(steps), encoding="utf-8")
        r = steps[-1].result
        scores.append(adherence(case, r.design if r else None, r.artifact if r else None))
    return scores


def gate(rig: Rig, base: LLM) -> Evidence:
    tuned, prompted = benchmark(rig, rig.llm, "candidate"), benchmark(rig, base, "base")
    report = {"candidate": [s.model_dump() for s in tuned], "base": [s.model_dump() for s in prompted]}
    (rig.out / "scores.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    a, b = statistics.mean(s.score for s in tuned), statistics.mean(s.score for s in prompted)
    m: Measured = {
        "candidate": rig.llm.name,
        "base": base.name,
        "cases": len(tuned),
        "candidate_score": round(a, 1),
        "base_score": round(b, 1),
    }
    note = "mean per-case share of house-style conventions followed (0-100); per case in scores.json"
    return evidence("CX-13", {**m, "gain": round(a - b, 1)}, a - b >= MARGIN, note=note)


def cx_13(rig: Rig) -> Evidence:
    return gate(rig, llm_for(rig.config, os.environ.get(BASE_ENV, BASE)))


ROWS: dict[str, Demo] = {"CX-13": cx_13}
