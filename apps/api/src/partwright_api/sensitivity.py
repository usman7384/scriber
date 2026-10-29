from collections.abc import Callable

from partwright_api.schemas import Sensitivity
from partwright_geometry import BuildError, PartMetrics, density
from partwright_ir import Design, ParamError, apply_params

Measure = Callable[[Design], list[PartMetrics]]
Totals = dict[str, float | None]
RELATIVE_STEP = 1e-3


def totals(design: Design, parts: list[PartMetrics]) -> Totals:
    materials = {p.id: p.material for p in design.parts}
    rhos = [density(m) if (m := materials.get(p.id)) else None for p in parts]
    masses = [p.volume * r / 1000 for p, r in zip(parts, rhos, strict=True) if r is not None]
    lo = [min(p.bbox_min[i] for p in parts) for i in range(3)]
    hi = [max(p.bbox_min[i] + p.bbox_size[i] for p in parts) for i in range(3)]
    sizes = {f"bbox_{axis}": hi[i] - lo[i] for i, axis in enumerate("xyz")}
    return {"volume": sum(p.volume for p in parts), "mass_g": sum(masses) if len(masses) == len(parts) else None, **sizes}


def sensitivities(design: Design, measure: Measure, names: list[str] | None = None) -> tuple[Totals, list[Sensitivity]]:
    base = totals(design, measure(design))
    chosen = [p.name for p in design.params if p.unit in ("mm", "deg") and (names is None or p.name in names)]
    return base, [_central(design, measure, base, name) for name in chosen]


def _central(design: Design, measure: Measure, base: Totals, name: str) -> Sensitivity:
    p = next(p for p in design.params if p.name == name)
    h = RELATIVE_STEP * max(abs(p.value), 1.0)
    lo = p.value - h if p.min is None or p.value - h >= p.min else p.value
    hi = p.value + h if p.max is None or p.value + h <= p.max else p.value
    out = Sensitivity(name=name, value=p.value, unit=p.unit, step=hi - lo, d={})
    if hi == lo:
        return out.model_copy(update={"error": "the bounds leave no room for a step"})
    try:
        a, b = (base if v == p.value else totals(design, measure(apply_params(design, {name: v}))) for v in (lo, hi))
    except (BuildError, ParamError) as e:
        return out.model_copy(update={"error": str(e)})
    return out.model_copy(update={"d": {k: _slope(a[k], b[k], hi - lo) for k in base}})


def _slope(a: float | None, b: float | None, step: float) -> float | None:
    return None if a is None or b is None else (b - a) / step
