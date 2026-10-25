from pathlib import Path

from partwright_context import Fact
from partwright_evals.grounded import LabelFact, LabelRule, load_cases, score_facts, score_rules
from partwright_ir import Provenance, Rule, RuleSet

SRC = Provenance(source="document", ref="d#p1:l1")


def fact(kind: str, value: float | str, **extra: object) -> Fact:
    return Fact.model_validate(
        {
            "id": f"f{value}",
            "doc_id": "d",
            "kind": kind,
            "name": "n",
            "value": value,
            "page": 1,
            "line": 1,
            "text": "t",
            "source": SRC,
            **extra,
        }
    )


def test_cases_load_and_have_fixtures() -> None:
    root = Path(__file__).parents[1] / "grounded"
    cases = load_cases(root / "cases.yaml")
    assert len(cases) == 10
    assert all((root / "files" / c.id).is_dir() for c in cases)


def test_fact_scoring_counts_each_fact_once() -> None:
    labels = [LabelFact(kind="parameter", value=80), LabelFact(kind="parameter", value=80), LabelFact(kind="holes", value=6, count=4)]
    facts = [fact("parameter", 80.0), fact("holes", 6.0, count=4), fact("parameter", 3.0)]
    score, matched = score_facts(labels, facts)
    assert (score.tp, score.fp, score.fn) == (2, 1, 1)
    assert len(matched) == 2


def test_rule_scoring_ignores_defaults() -> None:
    project = Rule(id="e", kind="min_hole_edge_ratio", value=2, unit="", source=SRC)
    default = Rule(id="w", kind="min_wall_thickness", value=0.8, unit="mm")
    score = score_rules(
        [LabelRule(kind="min_hole_edge_ratio", value=2), LabelRule(kind="max_overhang_angle", value=45)], RuleSet(rules=[project, default])
    )
    assert (score.tp, score.fp, score.fn) == (1, 0, 1)
