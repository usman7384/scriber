from partwright_ir import Rule, RuleSet

EDGE = Rule(id="hole-edge", kind="min_hole_edge_ratio", value=1.5, unit="")
CORNER = Rule(id="mill-corner", kind="min_internal_corner_radius", value=3, unit="mm", process="milling_3axis")
OVERHANG = Rule(id="fdm-overhang", kind="max_overhang_angle", value=45, unit="deg", process="fdm", binding="dynamic", severity="warning")


def test_for_process_keeps_generic_and_matching_rules() -> None:
    rules = RuleSet(rules=[EDGE, CORNER, OVERHANG])
    assert [r.id for r in rules.for_process("fdm").rules] == ["hole-edge", "fdm-overhang"]


def test_project_override_replaces_rule_with_same_id() -> None:
    stricter = EDGE.model_copy(update={"value": 2.0})
    merged = RuleSet(rules=[EDGE, CORNER]).merged(RuleSet(rules=[stricter]))
    assert [(r.id, r.value) for r in merged.rules] == [("mill-corner", 3), ("hole-edge", 2.0)]
