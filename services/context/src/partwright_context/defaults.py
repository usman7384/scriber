from partwright_ir import Rule, RuleSet

DEFAULT_RULES = RuleSet(
    rules=[
        Rule(id="min_hole_edge_ratio", kind="min_hole_edge_ratio", value=1.5, unit="", text="hole-to-edge distance at least 1.5 x D"),
        Rule(id="min_wall_thickness", kind="min_wall_thickness", value=0.8, unit="mm", text="minimum wall thickness 0.8 mm"),
        Rule(id="min_hole_diameter", kind="min_hole_diameter", value=1.0, unit="mm", text="minimum hole diameter 1 mm"),
        Rule(
            id="min_internal_corner_radius@milling_3axis",
            kind="min_internal_corner_radius",
            value=1.5,
            unit="mm",
            process="milling_3axis",
            text="internal corners at least the radius of a 3 mm end mill",
        ),
        Rule(
            id="max_overhang_angle@fdm",
            kind="max_overhang_angle",
            value=45,
            unit="deg",
            process="fdm",
            severity="warning",
            binding="dynamic",
            text="overhangs beyond 45 degrees need support",
        ),
    ]
)
