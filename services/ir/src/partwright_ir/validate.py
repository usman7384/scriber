from collections.abc import Iterator

from pydantic import BaseModel

from partwright_ir.expr import ExprError, evaluate, names
from partwright_ir.model import Design, Expr, Extrude, Feature, Hole, Part, Provenance, Revolve

NON_EXPR_FIELDS = {"id", "name", "intent", "sketch", "kind", "mode", "axis", "edges", "open_face", "base"}
POSITIVE_FIELDS = {"width", "height", "diameter", "length", "radius", "thickness", "count", "count_x", "count_y"}


class IrError(BaseModel):
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def validate(design: Design) -> list[IrError]:
    part_errors = [e for i, p in enumerate(design.parts) for e in _part_errors(design, p, f"parts[{i}]")]
    return [*_param_errors(design), *part_errors, *_unused_params(design)]


def _param_errors(design: Design) -> Iterator[IrError]:
    seen: set[str] = set()
    for p in design.params:
        if p.name in seen:
            yield IrError(path=f"params.{p.name}", message="duplicate parameter name")
        seen.add(p.name)
        if (p.min is not None and p.value < p.min) or (p.max is not None and p.value > p.max):
            yield IrError(path=f"params.{p.name}", message=f"value {p.value} outside [{p.min}, {p.max}]")


def _unused_params(design: Design) -> Iterator[IrError]:
    used = {n for part in design.parts for node in [*part.sketches, *part.features] for n in _names(node)}
    for p in design.params:
        if p.name not in used:
            yield IrError(
                path=f"params.{p.name}", message="defined but not used; reference it in feature expressions instead of a literal number"
            )


def _names(node: BaseModel) -> Iterator[str]:
    for name, value in node:
        if isinstance(value, Provenance) or name in NON_EXPR_FIELDS:
            continue
        if isinstance(value, BaseModel):
            yield from _names(value)
        elif isinstance(value, list | tuple):
            for item in value:
                yield from _names(item) if isinstance(item, BaseModel) else _item_names(item)
        else:
            yield from _item_names(value)


def _item_names(value: object) -> Iterator[str]:
    if isinstance(value, list | tuple):
        for v in value:
            yield from _item_names(v)
    elif isinstance(value, str):
        try:
            yield from names(value)
        except ExprError:
            return


def _part_errors(design: Design, part: Part, path: str) -> Iterator[IrError]:
    values = design.param_values()
    sketch_ids = [s.id for s in part.sketches]
    if len(set(sketch_ids)) != len(sketch_ids):
        yield IrError(path=f"{path}.sketches", message="duplicate sketch id")
    for s in part.sketches:
        yield from _exprs(s, values, f"{path}.sketches.{s.id}")
    feature_ids = [f.id for f in part.features]
    if len(set(feature_ids)) != len(feature_ids):
        yield IrError(path=f"{path}.features", message="duplicate feature id")
    if not isinstance(part.features[0], Extrude | Revolve) or part.features[0].mode != "add":
        yield IrError(path=f"{path}.features[0]", message="first feature must be an additive extrude or revolve")
    for f in part.features:
        yield from _feature_errors(f, sketch_ids, values, f"{path}.features.{f.id}")


def _feature_errors(f: Feature, sketch_ids: list[str], values: dict[str, float], path: str) -> Iterator[IrError]:
    if isinstance(f, Extrude | Revolve) and f.sketch not in sketch_ids:
        yield IrError(path=path, message=f"unknown sketch {f.sketch!r}; known: {sketch_ids}")
    if isinstance(f, Hole) and (f.counterbore_diameter is None) != (f.counterbore_depth is None):
        yield IrError(path=path, message="counterbore needs both diameter and depth")
    yield from _exprs(f, values, path)


def _exprs(node: BaseModel, values: dict[str, float], path: str) -> Iterator[IrError]:
    for name, value in node:
        sub = f"{path}.{name}"
        if isinstance(value, Provenance):
            continue
        if isinstance(value, BaseModel):
            yield from _exprs(value, values, sub)
        elif isinstance(value, list | tuple):
            for i, item in enumerate(value):
                if isinstance(item, BaseModel):
                    yield from _exprs(item, values, f"{sub}[{i}]")
                elif isinstance(item, tuple | list):
                    yield from (e for j, x in enumerate(item) for e in _expr(x, values, f"{sub}[{i}][{j}]", False))
                else:
                    yield from _expr(item, values, f"{sub}[{i}]", False)
        elif isinstance(value, float | int | str) and not isinstance(value, bool) and name not in NON_EXPR_FIELDS:
            yield from _expr(value, values, sub, name in POSITIVE_FIELDS, name == "distance")


def _expr(value: Expr, values: dict[str, float], path: str, positive: bool, nonzero: bool = False) -> Iterator[IrError]:
    try:
        result = evaluate(value, values)
    except ExprError as e:
        yield IrError(path=path, message=str(e))
        return
    if positive and result <= 0:
        yield IrError(path=path, message=f"must be > 0, got {result:g}")
    if nonzero and result == 0:
        yield IrError(path=path, message="must not be 0")
