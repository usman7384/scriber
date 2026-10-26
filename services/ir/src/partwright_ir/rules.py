from typing import Literal

from pydantic import Field

from partwright_ir.model import Frozen, Process, Provenance

RuleKind = Literal[
    "min_hole_edge_ratio",
    "min_wall_thickness",
    "min_hole_diameter",
    "max_overall_size",
    "min_internal_corner_radius",
    "max_overhang_angle",
]


class Rule(Frozen):
    id: str
    kind: RuleKind
    value: float
    unit: Literal["mm", "deg", ""]
    process: Process = "any"
    severity: Literal["error", "warning"] = "error"
    binding: Literal["static", "dynamic"] = "static"
    text: str = ""
    source: Provenance = Provenance(source="default")


class RuleSet(Frozen):
    rules: list[Rule] = Field(default_factory=list)

    def for_process(self, process: Process) -> "RuleSet":
        return RuleSet(rules=[r for r in self.rules if r.process in ("any", process)])

    def merged(self, overrides: "RuleSet") -> "RuleSet":
        replaced = {r.id for r in overrides.rules}
        return RuleSet(rules=[*(r for r in self.rules if r.id not in replaced), *overrides.rules])


class ShapeDescriptor(Frozen):
    bbox_sorted: tuple[float, float, float]
    volume: float
    area: float
    hole_diameters: list[float] = Field(default_factory=list)
    face_kinds: dict[str, int] = Field(default_factory=dict)
