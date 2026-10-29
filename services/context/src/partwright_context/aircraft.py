from typing import Any

from partwright_context.sizing import AircraftSpec, Sourced
from partwright_ir import Design, Param, Provenance

Expr = str | float


def aircraft_design(spec: AircraftSpec) -> Design:
    wing, body, tail = spec.wing, spec.body, spec.tail
    if body and body.width.value >= wing.span.value:
        raise ValueError(f"{spec.source}: body width {body.width.value:g} mm must be less than the span {wing.span.value:g} mm")
    origin = Provenance(source="document", ref=spec.source)
    params = [
        _param("wing_span", wing.span, "mm", "projected tip-to-tip span"),
        _param("root_chord", wing.root_chord, "mm", "chord where the outer wing starts"),
        _param("tip_chord", wing.tip_chord, "mm", "chord at the wing tip"),
        _param("sweep", wing.sweep, "deg", "leading-edge sweep of the outer wing"),
        _param("dihedral", wing.dihedral, "deg", "leading-edge dihedral of the outer wing"),
        _param("twist", wing.twist, "deg", "washout: tip nose-down relative to the root"),
    ]
    inner: Expr = "body_width / 2" if body else 0.0
    root_x: Expr = "body_chord - root_chord" if body else 0.0
    panel = "(wing_span - body_width) / 2" if body else "wing_span / 2"
    tip_x = f"{root_x} + {panel} * tan(sweep)" if body else f"{panel} * tan(sweep)"
    tip_z = f"{panel} * tan(dihedral)"
    wing_root = "mid_airfoil" if body else "root_airfoil"
    features: list[dict[str, Any]] = []
    if body:
        params += [_param("body_chord", body.chord, "mm", "centre-body chord"), _param("body_width", body.width, "mm", "centre-body width")]
        features.append(_section("root_airfoil", "XZ", 0.0, body.naca, "body_chord", (0.0, 0.0)))
    features += [
        _section(wing_root, "XZ", inner, wing.naca, "root_chord", (root_x, 0.0)),
        _section("tip_airfoil", "XZ", "wing_span / 2", wing.naca, "tip_chord", (tip_x, tip_z), "-twist"),
    ]
    features.append(_loft("main_wing", [f["id"] for f in features], ruled=body is None))
    if tail:
        params += [
            _param("tail_span", tail.span, "mm", "height of each wing-tip fin"),
            _param("tail_tip_chord", tail.tip_chord, "mm", "chord at the fin tip"),
            _param("tail_sweep", tail.sweep, "deg", "leading-edge sweep of the fins"),
        ]
        y = f"-(wing_span / 2 - {int(tail.naca[2:]) / 100:g} * tip_chord)"
        features += [
            _section("winglet_root_airfoil", "XY", tip_z, tail.naca, "tip_chord", (tip_x, y)),
            _section(
                "winglet_tip_airfoil",
                "XY",
                f"{tip_z} + tail_span",
                tail.naca,
                "tail_tip_chord",
                (f"{tip_x} + tail_span * tan(tail_sweep)", y),
            ),
            _loft("winglet", ["winglet_root_airfoil", "winglet_tip_airfoil"], ruled=True),
            _mirror("winglet_assembly", "winglet"),
        ]
    features.append(_mirror("full_aircraft", "main_wing"))
    features = [{**f, "provenance": origin.model_dump()} for f in features]
    part = {"id": "aircraft", "name": spec.name, "sketches": [], "features": features}
    return Design.model_validate({"title": spec.name[:60], "params": [p.model_dump() for p in params], "parts": [part]})


def _param(name: str, source: Sourced, unit: str, description: str) -> Param:
    low, high = (1.0, None) if unit == "mm" else (-60.0, 60.0)
    return Param(name=name, value=source.value, unit=unit, min=low, max=high, description=description, provenance=source.provenance)


def _section(sid: str, base: str, offset: Expr, naca: str, chord: str, le: tuple[Expr, Expr], twist: Expr = 0.0) -> dict[str, Any]:
    plane = {"ref": base, "offset": offset}
    intent = f"NACA {naca} section"
    return {
        "kind": "airfoil_section",
        "id": sid,
        "name": sid,
        "intent": intent,
        "plane": plane,
        "naca": naca,
        "chord": chord,
        "leading_edge": le,
        "twist": twist,
    }


def _loft(fid: str, sections: list[str], ruled: bool) -> dict[str, Any]:
    return {"kind": "loft", "id": fid, "name": fid, "sections": sections, "ruled": ruled}


def _mirror(fid: str, source: str) -> dict[str, Any]:
    return {"kind": "pattern", "id": fid, "name": fid, "features": [source], "type": "mirror", "mirror_plane": "XZ"}
