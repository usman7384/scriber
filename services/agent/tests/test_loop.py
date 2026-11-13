import json
from pathlib import Path

from scriber_agent import FakeLLM, generate, refine
from scriber_geometry import Artifact, BuildError, Finding, HoleInfo, PartMetrics
from scriber_ir import Design, Process, RuleSet

NO_RULES = RuleSet()

REQS = json.dumps(
    {
        "requirements": [
            {"kind": "extent", "description": "plate 80 mm", "value": 80},
            {"kind": "holes", "description": "4x M6", "count": 4, "diameter_min": 6.4, "diameter_max": 7.0},
        ]
    }
)


def design(hole_param: str = "hole_d", length: float = 80) -> str:
    return json.dumps(
        {
            "title": "Bracket",
            "params": [{"name": "length", "value": length, "unit": "mm"}, {"name": "hole_d", "value": 6.6, "unit": "mm"}],
            "parts": [
                {
                    "id": "p",
                    "name": "Plate",
                    "sketches": [{"id": "s", "entities": [{"kind": "rect", "width": "length", "height": 60}]}],
                    "features": [
                        {"kind": "extrude", "id": "e", "name": "Plate", "sketch": "s", "distance": 5},
                        {
                            "kind": "hole",
                            "id": "h",
                            "name": "Holes",
                            "plane": {"offset": 5},
                            "at": {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": 60, "spacing_y": 40},
                            "diameter": hole_param,
                        },
                    ],
                }
            ],
        }
    )


class FakeGeometry:
    def __init__(self, fail_first: bool = False) -> None:
        self.fail_first = fail_first
        self.built: list[Design] = []
        self.rules: list[RuleSet] = []

    def build(self, d: Design, out_dir: Path, rules: RuleSet = NO_RULES, process: Process = "any") -> Artifact:
        self.built.append(d)
        self.rules.append(rules)
        if self.fail_first and len(self.built) == 1:
            raise BuildError("kernel", "Standard_Failure: BRep_API: command not done")
        v = d.param_values()
        holes = [HoleInfo(diameter=v["hole_d"], axis=(0, 0, 1), center=(x, y, 2.5), length=5) for x in (-30, 30) for y in (-20, 20)]
        part = PartMetrics(
            id="p",
            name="Plate",
            volume=1.0,
            bbox_min=(0, 0, 0),
            bbox_size=(v["length"], 60, 5),
            solids=1,
            faces=10,
            valid=True,
            holes=holes,
        )
        return Artifact(design_hash="x", files={"glb": out_dir / "model.glb"}, parts=[part], findings=[], elapsed_ms=1)

    def thumbnail(self, glb: Path, png: Path, size: int = 256, view: str = "iso") -> Path:
        png.write_bytes(b"render")
        return png


def test_invalid_ir_is_repaired(tmp_path: Path) -> None:
    llm = FakeLLM([REQS, design(hole_param="bolt_d"), design()])
    steps = list(generate("bracket 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path))
    assert [s.kind for s in steps] == ["requirements", "emit", "check", "repair", "done"]
    assert "unknown parameter 'bolt_d'" in steps[2].message
    assert "unknown parameter 'bolt_d'" in llm.calls[-1][-1].content
    result = steps[-1].result
    assert result and result.ok and result.repairs == 1


def test_unmet_requirement_triggers_repair(tmp_path: Path) -> None:
    llm = FakeLLM([REQS, design(length=70), design()])
    steps = list(generate("bracket 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path))
    assert "requirement not met: plate 80 mm" in steps[2].message
    assert steps[-1].kind == "done"


def test_kernel_error_triggers_repair(tmp_path: Path) -> None:
    steps = list(generate("bracket 80 x 60, 4x M6", FakeLLM([REQS, design(), design(), design()]), FakeGeometry(fail_first=True), tmp_path))
    assert "CAD kernel error (kernel)" in steps[2].message
    assert steps[-1].kind == "done"


def test_gives_up_after_max_repairs(tmp_path: Path) -> None:
    llm = FakeLLM([REQS, "not json", "still not json", "not json either"])
    steps = list(generate("bracket 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path, max_repairs=2))
    assert steps[-1].kind == "failed"
    assert steps[-1].result and steps[-1].result.attempts == 3


def test_refine_with_parameter_update_keeps_everything_else(tmp_path: Path) -> None:
    original = Design.model_validate_json(design())
    answer = json.dumps({"updates": [{"name": "length", "value": 90}], "design": None})
    reqs = json.dumps({"requirements": [{"kind": "extent", "description": "length 90", "value": 90}]})
    steps = list(refine(original, "make it 90 mm long", FakeLLM([reqs, answer]), FakeGeometry(), tmp_path))
    result = steps[-1].result
    assert steps[-1].kind == "done" and result and result.design
    assert result.design.param_values() == {"length": 90, "hole_d": 6.6}
    assert result.design.parts == original.parts


def test_finding_suggestion_reaches_the_repair_prompt(tmp_path: Path) -> None:
    class EdgeGeometry(FakeGeometry):
        def build(self, d: Design, out_dir: Path, rules: RuleSet = NO_RULES, process: Process = "any") -> Artifact:
            art = super().build(d, out_dir, rules, process)
            if len(self.built) > 1:
                return art
            bad = Finding(rule_id="hole-edge", severity="error", message="hole too close", part="p", suggestion="move it to >= 15 mm")
            return art.model_copy(update={"findings": [bad]})

    llm = FakeLLM([REQS, design(), design(), design()])
    steps = list(generate("bracket 80 x 60, 4x M6", llm, EdgeGeometry(), tmp_path))
    assert "Fix: move it to >= 15 mm." in llm.calls[-1][-1].content
    assert steps[-1].kind == "done"


def test_unused_params_are_dropped_before_validation(tmp_path: Path) -> None:
    extra = json.loads(design())
    extra["params"].append({"name": "min_wall", "value": 3, "unit": "mm"})
    steps = list(generate("bracket 80 x 60, 4x M6", FakeLLM([REQS, json.dumps(extra)]), FakeGeometry(), tmp_path))
    result = steps[-1].result
    assert steps[-1].kind == "done" and result and result.design
    assert [p.name for p in result.design.params] == ["length", "hole_d"]


def test_cut_off_answer_is_not_quoted_back(tmp_path: Path) -> None:
    llm = FakeLLM([REQS, '{"title": "Bracket", "params": [', design()])
    steps = list(generate("bracket 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path))
    repair = llm.calls[-1][-1].content
    assert "was not complete JSON" in repair and "Invalid JSON" in repair
    assert '"title": "Bracket", "params": [' not in repair
    assert steps[-1].kind == "done"


def test_repeated_answer_is_resampled_without_quoting_it(tmp_path: Path) -> None:
    short = design(length=70)
    llm = FakeLLM([REQS, short, short, design()])
    steps = list(generate("bracket 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path))
    resample = llm.calls[-1][-1].content
    assert "kept returning the same design" in resample and "requirement not met: plate 80 mm" in resample
    assert short not in resample
    assert "re-sampled" in steps[-2].message
    assert steps[-1].kind == "done" and steps[-1].result and steps[-1].result.attempts == 2


def test_quote_not_in_the_request_drops_the_citation_not_the_part(tmp_path: Path) -> None:
    def quoting(quote: str) -> str:
        d = json.loads(design())
        d["params"][0]["provenance"] = {"source": "prompt", "quote": quote}
        return json.dumps(d)

    llm = FakeLLM([REQS, quoting("80 mm long")])
    steps = list(generate("bracket 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path))
    result = steps[-1].result
    assert steps[-1].kind == "done" and steps[-1].attempt == 1
    assert result is not None and result.design is not None and result.design.params[0].provenance.source == "default"


def test_images_reach_the_design_request(tmp_path: Path) -> None:
    llm = FakeLLM([REQS, design()])
    list(generate("bracket like the sketch, 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path, images=(b"png",)))
    assert llm.calls[0][-1].images == () and llm.calls[1][-1].images == (b"png",)
    llm = FakeLLM([REQS, json.dumps({"updates": [{"name": "length", "value": 90}], "design": None})])
    list(refine(Design.model_validate_json(design()), "like the photo", llm, FakeGeometry(), tmp_path / "r", images=(b"jpg",)))
    assert llm.calls[1][-1].images == (b"jpg",)


def test_thinking_level_sets_the_reasoning_budget(tmp_path: Path) -> None:
    logs = {}
    for level in ("low", "high"):
        llm = FakeLLM([REQS, design()])
        steps = list(generate("bracket 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path / level, thinking=level))
        assert steps[-1].kind == "done" and llm.budgets == [None, {"low": 0, "high": 8192}[level]]
        logs[level] = steps[1].message
    assert logs["low"].endswith("thinking low with a 0 token reasoning budget")
    assert logs["high"].endswith("thinking high with a 8192 token reasoning budget")


def test_requests_with_images_go_to_the_vision_model(tmp_path: Path) -> None:
    text, vision = FakeLLM([REQS]), FakeLLM([NO_REQS, design(), MATCH])
    steps = list(generate("bracket like the sketch, 80 x 60, 4x M6", text, FakeGeometry(), tmp_path, images=(b"png",), vision=vision))
    assert steps[-1].kind == "done" and len(text.calls) == 1 and len(vision.calls) == 3
    assert vision.calls[1][-1].images == (b"png",) and '"source": "vision"' in vision.calls[1][-1].content
    text, vision = FakeLLM([REQS, design()]), FakeLLM([])
    list(generate("bracket 80 x 60, 4x M6", text, FakeGeometry(), tmp_path / "t", vision=vision))
    assert "vision" not in text.calls[1][-1].content and vision.calls == []
    text, vision = FakeLLM([REQS]), FakeLLM([json.dumps({"updates": [{"name": "length", "value": 90}], "design": None})])
    base = Design.model_validate_json(design())
    list(refine(base, "like the photo", text, FakeGeometry(), tmp_path / "r", images=(b"jpg",), vision=vision))
    assert vision.calls[0][-1].images == (b"jpg",)


DRAWN = json.dumps(
    {
        "requirements": [
            {"kind": "holes", "description": "4X 6.6 THRU", "count": 4, "diameter_min": 6.5, "diameter_max": 6.7},
            {"kind": "extent", "description": "overall 200", "value": 200},
        ]
    }
)
NO_REQS = json.dumps({"requirements": []})
MISMATCH = json.dumps({"findings": ["the chamfers are missing"], "matches": False})
MATCH = json.dumps({"findings": [], "matches": True})


def test_drawing_dimensions_become_checks_and_the_critic_can_send_a_part_back(tmp_path: Path) -> None:
    vision = FakeLLM([DRAWN, design(), MISMATCH, design(length=81), MATCH])
    steps = list(generate("Reproduce the drawing.", FakeLLM([NO_REQS]), FakeGeometry(), tmp_path, images=(b"drawing",), vision=vision))
    assert vision.calls[0][-1].images == (b"drawing",)
    assert [s.kind for s in steps] == ["requirements", "emit", "check", "repair", "done"]
    assert "compared with the attached image: the chamfers are missing" in steps[2].message
    assert vision.calls[2][-1].images == (b"drawing", b"render", b"render", b"render")
    result = steps[-1].result
    assert result is not None and [c.requirement.kind for c in result.checks] == ["holes"]


def test_the_critic_cannot_use_up_every_repair(tmp_path: Path) -> None:
    worse = json.dumps({"findings": ["the chamfers are missing", "the outline is wrong"], "matches": False})
    vision = FakeLLM([NO_REQS, design(), MISMATCH, design(length=81), MISMATCH, design(length=82), worse])
    steps = list(generate("Reproduce the drawing.", FakeLLM([NO_REQS]), FakeGeometry(), tmp_path, images=(b"drawing",), vision=vision))
    result = steps[-1].result
    assert steps[-1].kind == "done" and steps[-1].attempt == 3
    assert result is not None and result.attempts == 2 and "kept attempt 2" in steps[-1].message


def test_a_check_that_keeps_failing_is_set_aside(tmp_path: Path) -> None:
    misread = json.dumps({"requirements": [{"kind": "extent", "description": "base 15", "value": 15}]})
    llm = FakeLLM([misread, design(), design(length=81), design(length=82)])
    steps = list(generate("plate 80 x 60 x 5 on a 15 mm base", llm, FakeGeometry(), tmp_path, max_repairs=5))
    assert steps[-1].kind == "done" and steps[-1].attempt == 3
    assert any("set aside after 3 failed attempts, probably misread: base 15" in s.message for s in steps)


def test_an_empty_answer_is_asked_again_without_spending_a_repair(tmp_path: Path) -> None:
    llm = FakeLLM([REQS, "", design()])
    steps = list(generate("bracket 80 x 60, 4x M6", llm, FakeGeometry(), tmp_path, max_repairs=0))
    assert steps[-1].kind == "done" and steps[-1].attempt == 1
    assert "output limit was reached" in llm.calls[2][-1].content


def test_a_failed_run_keeps_its_best_attempt(tmp_path: Path) -> None:
    llm = FakeLLM([REQS, design(), design(hole_param="nope"), design(hole_param="nope2")])
    reqs_fail = json.dumps({"requirements": [{"kind": "extent", "description": "plate 90", "value": 90}]})
    llm = FakeLLM([reqs_fail, design(), design(hole_param="nope"), design(hole_param="nope2")])
    steps = list(generate("bracket 90 x 60", llm, FakeGeometry(), tmp_path, max_repairs=2))
    assert steps[-1].kind == "failed" and "kept attempt 1" in steps[-1].message
    result = steps[-1].result
    assert result is not None and result.artifact is not None


def test_a_set_aside_check_does_not_fail_the_verdict(tmp_path: Path) -> None:
    misread = json.dumps({"requirements": [{"kind": "extent", "description": "base 15", "value": 15}]})
    llm = FakeLLM([misread, design(), design(length=81), design(length=82)])
    steps = list(generate("plate 80 x 60 x 5 on a 15 mm base", llm, FakeGeometry(), tmp_path, max_repairs=5))
    result = steps[-1].result
    assert steps[-1].kind == "done" and result is not None and result.ok and result.disputed == ["base 15"]


def test_a_dense_drawing_is_built_up_in_stages(tmp_path: Path) -> None:
    whole = json.loads(design())
    hole = whole["parts"][0]["features"].pop()
    plan = {"stages": [{"name": "plate", "views": "top", "features": "the plate"}, {"name": "holes", "views": "top", "features": "4x M6"}]}
    holes = json.dumps({"part": "p", "features": [hole]})
    broken = json.dumps({"part": "q", "features": [hole]})
    text, vision = FakeLLM([REQS]), FakeLLM([NO_REQS, json.dumps(plan), json.dumps(whole), broken, holes, MATCH])
    geometry = FakeGeometry()
    steps = list(generate("bracket as drawn", text, geometry, tmp_path, images=(b"png",), vision=vision, staged=True))
    assert [s.kind for s in steps] == ["requirements", "plan", "build", "build", "emit", "done"]
    assert steps[1].message == "1. plate; 2. holes" and "stage 2, holes: built" in steps[3].message
    assert "the parts are ['p']" in vision.calls[4][-1].content
    assert "built up in stages" in steps[4].message
    assert [f.id for f in geometry.built[-1].parts[0].features] == ["e", "h"]
    assert vision.responses == []


def test_a_long_design_is_repaired_by_its_changes(tmp_path: Path) -> None:
    long = json.loads(design())
    long["params"][1] |= {"value": 3.0, "description": "hole " * 3000}
    fix = json.dumps({"part": "p", "params": [{"name": "hole_d", "value": 6.6, "unit": "mm"}]})
    llm = FakeLLM([REQS, json.dumps(long), fix])
    geometry = FakeGeometry()
    steps = list(generate("bracket 80 x 60, 4x M6", llm, geometry, tmp_path))
    assert [s.kind for s in steps] == ["requirements", "emit", "check", "repair", "done"]
    repair = llm.calls[2]
    assert repair[-2].role == "assistant" and "too long to write again" in repair[-1].content and "4x M6" in repair[-1].content
    assert geometry.built[-1].param_values()["hole_d"] == 6.6 and len(geometry.built[-1].parts[0].features) == 2
