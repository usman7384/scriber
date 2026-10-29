import json
from pathlib import Path

import pytest

from partwright_agent import FakeLLM, Grounding, context_block, generate
from partwright_agent.project_context import coverage, fact_requirements, overridden
from partwright_agent.requirements import CheckResult, Requirement
from partwright_context import ContextPack, Fact
from partwright_geometry import Artifact, HoleInfo, PartMetrics
from partwright_ir import Design, Process, Provenance, Rule, RuleSet

NO_RULES = RuleSet()
SOURCE = Provenance(source="document", ref="d1#p1:l3", quote="4 x M6 mounting holes")


def fact(fid: str, kind: str, name: str, value: float, **extra: object) -> Fact:
    return Fact.model_validate(
        {
            "id": fid,
            "doc_id": "d1",
            "kind": kind,
            "name": name,
            "value": value,
            "unit": "mm",
            "page": 1,
            "line": 3,
            "text": "spec line",
            "source": SOURCE,
            **extra,
        }
    )


HOLES = fact("d1:1.3.0", "holes", "req_2_mounting", 6.0, count=4, text="REQ-2 Mounting: 4 x M6 through holes")
BORE = fact("d1:1.4.0", "tolerance", "req_3_sensor_bore", 82.0, tol=(-0.2, 0.2), text="Ø82 ±0.2 mm bore")
LENGTH = fact("d1:1.5.0", "parameter", "plate_size_x", 80.0)
EDGE = Rule(id="min_hole_edge_ratio", kind="min_hole_edge_ratio", value=1.5, unit="", text="hole-to-edge at least 1.5 x D")


class FakeGeometry:
    def __init__(self) -> None:
        self.rules: list[RuleSet] = []

    def build(self, d: Design, out_dir: Path, rules: RuleSet = NO_RULES, process: Process = "any") -> Artifact:
        self.rules.append(rules)
        holes = [HoleInfo(diameter=6.6, axis=(0, 0, 1), center=(x, y, 2.5), length=5) for x in (-30, 30) for y in (-20, 20)]
        part = PartMetrics(
            id="p", name="P", volume=1, bbox_min=(0, 0, 0), bbox_size=(80, 60, 5), solids=1, faces=10, valid=True, holes=holes
        )
        return Artifact(design_hash="x", files={}, parts=[part], findings=[], elapsed_ms=1)


def design() -> dict[str, object]:
    holes = {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": 60, "spacing_y": 40}
    return {
        "title": "Bracket",
        "params": [{"name": "length", "value": 80, "unit": "mm"}, {"name": "hole_d", "value": 6.6, "unit": "mm"}],
        "parts": [
            {
                "id": "p",
                "name": "Plate",
                "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "length", "height": 60}]}],
                "features": [
                    {"kind": "extrude", "id": "e", "name": "Plate", "sketch": "s", "distance": 5},
                    {"kind": "hole", "id": "h", "name": "Holes", "plane": {"offset": 5}, "at": holes, "diameter": "hole_d"},
                ],
            }
        ],
    }


def grounding() -> Grounding:
    pack = ContextPack(query="bracket", chunks=[], facts=[HOLES, BORE, LENGTH], rules=[EDGE], similar_parts=[], conventions=[])
    return Grounding(pack=pack, rules=RuleSet(rules=[EDGE]))


def test_facts_become_checkable_requirements() -> None:
    reqs = fact_requirements([HOLES, BORE, LENGTH])
    assert [(r.kind, r.count, r.diameter_min, r.diameter_max, r.value) for r in reqs] == [
        ("holes", 4, 6.4, 7.0, None),
        ("holes", None, 81.8, 82.2, None),
        ("extent", None, None, None, 80.0),
    ]


def test_generation_sees_facts_cites_them_and_passes_rules(tmp_path: Path) -> None:
    cited = design()
    cited["params"][1]["provenance"] = {"source": "document", "ref": HOLES.id}  # type: ignore[index]
    llm = FakeLLM([json.dumps({"requirements": []}), json.dumps(cited)])
    geometry = FakeGeometry()
    steps = list(
        generate(
            "bracket",
            llm,
            geometry,
            tmp_path,
            context=grounding().model_copy(update={"pack": grounding().pack.model_copy(update={"facts": [HOLES, LENGTH]})}),
        )
    )
    prompt = llm.calls[1][-1].content
    assert f"[{HOLES.id}]" in prompt
    assert "[min_hole_edge_ratio] hole-to-edge at least 1.5 x D" in prompt
    assert geometry.rules[0].rules == [EDGE]
    result = steps[-1].result
    assert steps[-1].kind == "done" and result and result.design
    assert result.design.params[1].provenance == SOURCE
    assert HOLES.id in result.used and "min_hole_edge_ratio" in result.used


M5_HOLES = Requirement(kind="holes", description="4 M5", count=4, diameter_min=5.3, diameter_max=5.8)


def test_request_values_override_conflicting_facts_of_the_same_kind() -> None:
    stated = [Requirement(kind="extent", description="length 100", value=100), M5_HOLES]
    assert overridden(stated, [HOLES, BORE, LENGTH]) == [HOLES, LENGTH]


def test_facts_that_agree_or_add_something_new_are_kept() -> None:
    assert overridden([Requirement(kind="extent", description="length 80", value=80)], [HOLES, BORE, LENGTH]) == []
    assert overridden([], [HOLES, BORE, LENGTH]) == []


def test_overridden_facts_leave_the_checks_and_the_prompt(tmp_path: Path) -> None:
    stated = {"requirements": [M5_HOLES.model_dump()]}
    llm = FakeLLM([json.dumps(stated), json.dumps(design())])
    steps = list(generate("plate with four M5 holes", llm, FakeGeometry(), tmp_path, max_repairs=0, context=grounding()))
    assert "the request overrides the project documents on: REQ-2 Mounting: 4 x M6 through holes" in steps[0].message
    assert f"[{HOLES.id}]" not in llm.calls[1][-1].content
    assert f"[{BORE.id}]" in llm.calls[1][-1].content


def test_coverage_maps_each_numeric_fact_to_its_check_or_none() -> None:
    wall = fact("d1:1.6.0", "parameter", "wall_thickness", 2.0)
    tight = fact("d1:1.7.0", "tolerance", "length", 80.0, tol=(-0.05, 0.05), text="length 80 ±0.05 mm")
    material = fact("d1:1.8.0", "material", "material", 0.0).model_copy(update={"value": "PETG"})
    reqs = fact_requirements([HOLES, LENGTH, tight])
    checks = [CheckResult(requirement=r, passed=r.kind == "holes", actual="") for r in reqs]
    covered = {f.id: c and c.passed for f, c in coverage([HOLES, LENGTH, tight, wall, material], checks)}
    assert len(reqs) == 3
    assert covered == {HOLES.id: True, LENGTH.id: False, tight.id: False, wall.id: None}


def test_hole_table_rows_reach_the_prompt_with_their_position() -> None:
    row = fact("d1:1.9.h1", "hole", "hole_h1", 6.6, at=(20.0, 15.0), text="H1 | 20 | 15 | 6.6")
    pack = ContextPack(query="plate", chunks=[], facts=[row], rules=[], similar_parts=[], conventions=[])
    assert "[d1:1.9.h1] hole_h1 = 6.6mm at x=20, y=15: H1 | 20 | 15 | 6.6" in context_block(Grounding(pack=pack, rules=NO_RULES))


def test_threads_held_by_inserts_or_taps_accept_tap_drill_to_insert_bore() -> None:
    bosses = fact("d1:1.4.0", "holes", "bosses", 3.0, count=4, text="Bosses: 4×M3 heat-set inserts")  # noqa: RUF001
    [r] = fact_requirements([bosses])
    assert r.count == 4
    assert (r.diameter_min, r.diameter_max) == pytest.approx((2.25, 4.35))
