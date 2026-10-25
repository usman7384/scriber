import json
from pathlib import Path

from partwright_agent import FakeLLM, Grounding, generate
from partwright_agent.project_context import fact_requirements
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


HOLES = fact("d1:1.3.0", "holes", "M6", 6.0, count=4)
BORE = fact("d1:1.4.0", "tolerance", "diameter", 82.0, tol=(-0.2, 0.2), text="Ø82 ±0.2 mm bore")
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
