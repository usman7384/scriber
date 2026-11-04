import math
from typing import Any

import pytest
from build123d import Pos, Shape, SlotOverall

from scriber_geometry.models import SketchDof, SketchGeo
from scriber_geometry.sketcher import remaining_dof, sketch_dof
from scriber_ir import Design
from scriber_ir.prelude import PRELUDE

HELPERS: dict[str, Any] = {}
exec(PRELUDE, HELPERS)

PATH_FILLETS = {
    "kind": "path",
    "start": [0, 0],
    "segments": [{"to": [60, 0]}, {"to": [60, 20], "fillet": 4}, {"to": [20, 20], "fillet": 6}, {"to": [20, 50]}, {"to": [0, 50]}],
}
PATH_ARCS = {
    "kind": "path",
    "start": [0, 0],
    "segments": [{"to": [40, 0]}, {"to": [40, 30], "arc": "ccw", "radius": 20}, {"to": [0, 30]}, {"to": [0, 0], "arc": "cw", "radius": 25}],
}
CASES: dict[str, tuple[dict[str, Any], Any]] = {
    "rect": ({"kind": "rect", "center": [5, -3], "width": "w", "height": 30}, lambda: HELPERS["_rect"](40, 30, 0)),
    "rounded": ({"kind": "rect", "width": "w", "height": 30, "corner_radius": 6}, lambda: HELPERS["_rect"](40, 30, 6)),
    "circle": ({"kind": "circle", "center": [3, 4], "diameter": 12}, None),
    "slot": ({"kind": "slot", "center": [10, 5], "length": "w", "width": 12, "angle": 30}, lambda: Pos(10, 5) * SlotOverall(40, 12, 30)),
    "fillets": (
        PATH_FILLETS,
        lambda: HELPERS["_path"](
            (0, 0),
            [
                ((60, 0), "none", 0, 0),
                ((60, 20), "none", 0, 4),
                ((20, 20), "none", 0, 6),
                ((20, 50), "none", 0, 0),
                ((0, 50), "none", 0, 0),
            ],
        ),
    ),
    "arcs": (
        PATH_ARCS,
        lambda: HELPERS["_path"](
            (0, 0), [((40, 0), "none", 0, 0), ((40, 30), "ccw", 20, 0), ((0, 30), "none", 0, 0), ((0, 0), "cw", 25, 0)]
        ),
    ),
    "polygon": ({"kind": "polygon", "points": [[0, 0], ["w", 0], [30, 25], [0, 10]]}, None),
    "collinear": ({"kind": "polygon", "points": [[0, 0], [21, 0], ["w", 0], [37, 0], [48, 0]]}, None),
}


def analyse(entity: dict[str, Any]) -> SketchDof:
    design = Design.model_validate(
        {
            "title": "t",
            "params": [{"name": "w", "value": 40, "unit": "mm"}],
            "parts": [
                {
                    "id": "p",
                    "name": "P",
                    "sketches": [{"id": "s", "entities": [entity]}],
                    "features": [{"kind": "extrude", "id": "e", "name": "E", "sketch": "s", "distance": 1}],
                }
            ],
        }
    )
    (dof,) = sketch_dof(design)
    return dof


def perimeter(geometry: list[SketchGeo]) -> float:
    total = 0.0
    for g in geometry:
        v = g.values
        if g.kind == "line":
            total += math.dist(v[:2], v[2:4])
        elif g.kind == "arc":
            total += v[2] * (v[4] - v[3])
        elif g.kind == "circle":
            total += 2 * math.pi * v[2]
    return total


@pytest.mark.parametrize("name", sorted(CASES))
def test_every_entity_is_fully_constrained_and_resolves(name: str) -> None:
    entity, built = CASES[name]
    dof = analyse(entity)
    assert dof.dof == 0
    assert dof.solve_error < 1e-6
    assert remaining_dof(dof.geometry, dof.constraints) == 0
    assert len({(c.kind, *c.refs) for c in dof.constraints}) == len(dof.constraints)
    if built:
        face: Shape[Any] = built()
        assert perimeter(dof.geometry) == pytest.approx(sum(e.length for e in face.edges()), abs=1e-6)


def test_plain_rect_is_held_by_its_four_ir_dimensions() -> None:
    dof = analyse(CASES["rect"][0])
    dims = [(c.kind, c.expr) for c in dof.constraints if c.expr is not None]
    assert dims == [("distance_x", "w"), ("distance_y", "30.0"), ("distance_x", "5.0 - w / 2"), ("distance_y", "-3.0 - 30.0 / 2")]
    assert [c.kind for c in dof.constraints].count("coincident") == 4
    assert len(dof.constraints) == 12 and dof.unknowns == 16


def test_dropping_a_dimension_leaves_one_degree_of_freedom() -> None:
    dof = analyse(CASES["fillets"][0])
    for i, c in enumerate(dof.constraints):
        if c.kind in ("radius", "distance_x", "distance_y"):
            assert remaining_dof(dof.geometry, dof.constraints[:i] + dof.constraints[i + 1 :]) == 1


def test_fillet_next_to_an_arc_is_reported_not_guessed() -> None:
    entity = PATH_ARCS | {"segments": [{"to": [40, 0], "fillet": 3}, *PATH_ARCS["segments"][1:]]}
    dof = analyse(entity)
    assert dof.dof is None and "fillet next to an arc" in dof.note
