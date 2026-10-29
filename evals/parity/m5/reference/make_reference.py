import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
Json = dict[str, Any]
Expr = float | str


def params(**values: float) -> list[Json]:
    return [{"name": n, "value": v, "unit": "" if n.endswith("count") else "mm"} for n, v in values.items()]


def rect(w: Expr, h: Expr, at: tuple[Expr, Expr] = (0, 0), subtract: bool = False) -> Json:
    return {"kind": "rect", "center": list(at), "width": w, "height": h, "subtract": subtract}


def circle(d: Expr, at: tuple[Expr, Expr] = (0, 0), subtract: bool = False) -> Json:
    return {"kind": "circle", "center": list(at), "diameter": d, "subtract": subtract}


def poly(*points: tuple[Expr, Expr]) -> Json:
    return {"kind": "polygon", "points": [list(p) for p in points]}


def sketch(sid: str, *entities: Json, ref: str = "XY", offset: Expr = 0) -> Json:
    return {"id": sid, "plane": {"ref": ref, "offset": offset}, "entities": list(entities)}


def extrude(fid: str, sk: str, distance: Expr | None, **extra: Any) -> Json:
    return {"kind": "extrude", "id": fid, "name": fid.replace("_", " ").capitalize(), "sketch": sk, "distance": distance, **extra}


def hole(fid: str, d: Expr, at: Json, ref: str = "XY", offset: Expr = 0, **extra: Any) -> Json:
    name = fid.replace("_", " ").capitalize()
    return {"kind": "hole", "id": fid, "name": name, "plane": {"ref": ref, "offset": offset}, "at": at, "diameter": d, **extra}


def pts(*xy: tuple[Expr, Expr]) -> Json:
    return {"kind": "points", "points": [list(p) for p in xy]}


def grid(nx: Expr, ny: Expr, sx: Expr, sy: Expr) -> Json:
    return {"kind": "grid", "count_x": nx, "count_y": ny, "spacing_x": sx, "spacing_y": sy}


def polar(n: Expr, d: Expr) -> Json:
    return {"kind": "polar", "count": n, "diameter": d}


def design(title: str, ps: list[Json], sketches: list[Json], features: list[Json]) -> Json:
    part = {"id": "part", "name": title, "sketches": sketches, "features": features}
    return {"title": title, "params": ps, "parts": [part]}


def plate(title: str, ps: list[Json], outline: list[Json], *features: Json, extra: tuple[Json, ...] = ()) -> Json:
    return design(title, ps, [sketch("outline", *outline), *extra], [extrude("body", "outline", "thickness"), *features])


def b01() -> Json:
    ps = params(length=140, width=90, thickness=6, hole_d=9, inset=10)
    at = grid(2, 2, "length - 2 * inset", "width - 2 * inset")
    return plate("Cover plate", ps, [rect("length", "width")], hole("corner_holes", "hole_d", at, offset="thickness"))


def b02() -> Json:
    ps = params(od=30, length=12, bore=10.5)
    return design(
        "Round spacer",
        ps,
        [sketch("disc", circle("od"))],
        [extrude("body", "disc", "length"), hole("bore", "bore", pts((0, 0)), offset="length")],
    )


def b03() -> Json:
    ps = params(size=40, wall=3, length=100, hole_d=6.5, end_gap=20)
    tube = sketch("section", rect("size", "size"), rect("size - 2 * wall", "size - 2 * wall", subtract=True))
    holes = hole("cross_holes", "hole_d", pts((0, "end_gap"), (0, "length - end_gap")), ref="XZ")
    return design("Square tube", ps, [tube], [extrude("body", "section", "length"), holes])


def b04() -> Json:
    ps = params(od=100, thickness=10, bore=40, bolt_count=6, pcd=80, hole_d=6.6)
    return design(
        "Bolt disc",
        ps,
        [sketch("disc", circle("od"))],
        [
            extrude("body", "disc", "thickness"),
            hole("bore", "bore", pts((0, 0)), offset="thickness"),
            hole("bolts", "hole_d", polar("bolt_count", "pcd"), offset="thickness"),
        ],
    )


def b05() -> Json:
    ps = params(od=28, width=10, bore=12, tap_d=4.2, tap_depth=9)
    return design(
        "Shaft collar",
        ps,
        [sketch("disc", circle("od"))],
        [
            extrude("body", "disc", "width"),
            hole("bore", "bore", pts((0, 0)), offset="width"),
            hole("set_screw", "tap_d", pts((0, "width / 2")), ref="YZ", offset="od / 2", depth="tap_depth", type="tapped", fastener="M5"),
        ],
    )


def b06() -> Json:
    ps = params(length=80, depth=30, height=40, bore=20, bore_height=25, bolt_d=9, bolt_pitch=60)
    return design(
        "Bearing block",
        ps,
        [sketch("footprint", rect("length", "depth"))],
        [
            extrude("body", "footprint", "height"),
            hole("bore", "bore", pts((0, "bore_height")), ref="XZ"),
            hole("bolts", "bolt_d", pts(("-bolt_pitch / 2", 0), ("bolt_pitch / 2", 0)), offset="height"),
        ],
    )


def b07() -> Json:
    ps = params(length=100, width=60, thickness=10, hole_d=5.5, cb_d=10, cb_depth=5.5, pitch_x=80, pitch_y=40)
    cb = hole("screws", "hole_d", grid(2, 2, "pitch_x", "pitch_y"), offset="thickness", type="counterbore", fastener="M5")
    cb |= {"cb_diameter": "cb_d", "cb_depth": "cb_depth"}
    return plate("Counterbored plate", ps, [rect("length", "width")], cb)


def angle(title: str, ps: list[Json], tall: str, extra_sketches: list[Json], extra: list[Json]) -> Json:
    profile = poly((0, 0), ("leg_a", 0), ("leg_a", "thickness"), ("thickness", "thickness"), ("thickness", tall), (0, tall))
    return design(
        title,
        ps,
        [sketch("profile", profile, ref="XZ"), *extra_sketches],
        [extrude("body", "profile", "width", extent="symmetric"), *extra],
    )


def b08() -> Json:
    ps = params(leg_a=60, leg_b=40, width=50, thickness=5, hole_d=6.6, hole_gap=25)
    holes = [
        hole("base_holes", "hole_d", pts((35, "-hole_gap / 2"), (35, "hole_gap / 2")), offset="thickness"),
        hole("upright_holes", "hole_d", pts(("-hole_gap / 2", 22.5), ("hole_gap / 2", 22.5)), ref="YZ", offset="thickness"),
    ]
    return angle("Unequal angle bracket", ps, "leg_b", [], holes)


def b09() -> Json:
    ps = params(length=80, outer_width=50, height=30, thickness=4, hole_d=6.6, hole_pitch=50)
    half, inner = "outer_width / 2", "outer_width / 2 - thickness"
    profile = poly(
        (f"-{half}", 0), (half, 0), (half, "height"), (inner, "height"), (inner, "thickness"),
        (f"-({inner})", "thickness"), (f"-({inner})", "height"), (f"-{half}", "height"),
    )  # fmt: skip
    return design(
        "U-channel bracket",
        ps,
        [sketch("profile", profile, ref="YZ")],
        [
            extrude("body", "profile", "length", extent="symmetric"),
            hole("base_holes", "hole_d", pts(("-hole_pitch / 2", 0), ("hole_pitch / 2", 0)), offset="thickness"),
        ],
    )


def b10() -> Json:
    ps = params(major_d=20, major_len=40, minor_d=12, minor_len=30, hole_d=5)
    profile = poly(
        (0, 0), ("major_d / 2", 0), ("major_d / 2", "major_len"), ("minor_d / 2", "major_len"),
        ("minor_d / 2", "major_len + minor_len"), (0, "major_len + minor_len"),
    )  # fmt: skip
    return design(
        "Stepped pin",
        ps,
        [sketch("profile", profile, ref="XZ")],
        [
            {"kind": "revolve", "id": "body", "name": "Body", "sketch": "profile", "axis": "Y"},
            hole("axial_hole", "hole_d", pts((0, 0)), offset="major_len + minor_len"),
        ],
    )


def b11() -> Json:
    ps = params(od=60, thickness=15, bore=8, hole_count=4, pcd=34, hole_d=12)
    return design(
        "Lightened disc",
        ps,
        [sketch("disc", circle("od"))],
        [
            extrude("body", "disc", "thickness"),
            hole("bore", "bore", pts((0, 0)), offset="thickness"),
            hole("lightening", "hole_d", polar("hole_count", "pcd"), offset="thickness"),
        ],
    )


def b12() -> Json:
    ps = params(length=120, width=80, thickness=12, recess_l=70, recess_w=40, recess_depth=5, hole_d=6.6, pitch_x=100, pitch_y=60)
    recess = sketch("recess", rect("recess_l", "recess_w"), ref="body.end")
    return plate(
        "Machine base",
        ps,
        [rect("length", "width")],
        extrude("recess", "recess", "recess_depth", mode="cut"),
        hole("holes", "hole_d", grid(2, 2, "pitch_x", "pitch_y"), offset="thickness"),
        extra=(recess,),
    )


def b13() -> Json:
    ps = params(od=8, length=20, tap_d=2.5)
    return design(
        "Round standoff",
        ps,
        [sketch("disc", circle("od"))],
        [extrude("body", "disc", "length"), hole("tap", "tap_d", pts((0, 0)), offset="length", type="tapped", fastener="M3")],
    )


def b14() -> Json:
    ps = params(size=60, thickness=20, seat_d=22, seat_depth=7, bore=10, hole_d=5.5, pitch=46)
    return plate(
        "Bearing housing",
        ps,
        [rect("size", "size")],
        hole("seat", "seat_d", pts((0, 0)), offset="thickness", depth="seat_depth"),
        hole("bore", "bore", pts((0, 0)), offset="thickness"),
        hole("screws", "hole_d", grid(2, 2, "pitch", "pitch"), offset="thickness"),
    )


def b15() -> Json:
    ps = params(size=70, thickness=6, pilot_d=38.5, hole_d=5.5, pitch=47.14)
    return plate(
        "NEMA 23 adapter plate",
        ps,
        [rect("size", "size")],
        hole("pilot", "pilot_d", pts((0, 0)), offset="thickness"),
        hole("screws", "hole_d", grid(2, 2, "pitch", "pitch"), offset="thickness"),
    )


def b16() -> Json:
    ps = params(length=60, width=40, thickness=3, hole_d=4.5, cs_d=9, pitch=20)
    cs = hole("screws", "hole_d", grid(3, 1, "pitch", 0), offset="thickness", type="countersink") | {"cs_diameter": "cs_d"}
    return plate("Hinge leaf", ps, [rect("length", "width")], cs)


def b17() -> Json:
    ps = params(od=50, height=40, wall=3, floor=3)
    return design(
        "Cup",
        ps,
        [sketch("disc", circle("od"))],
        [extrude("body", "disc", "height"), hole("cavity", "od - 2 * wall", pts((0, 0)), offset="height", depth="height - floor")],
    )


def b18() -> Json:
    ps = params(od=30, id=17, thickness=3)
    return design(
        "M16 washer",
        ps,
        [sketch("disc", circle("od"))],
        [extrude("body", "disc", "thickness"), hole("hole", "id", pts((0, 0)), offset="thickness")],
    )


def b19() -> Json:
    ps = params(length=120, width=80, thickness=8, open_l=90, open_w=50, hole_d=4.5, pitch_x=105, pitch_y=65)
    outline = [rect("length", "width"), rect("open_l", "open_w", subtract=True)]
    return plate("Window frame", ps, outline, hole("corner_holes", "hole_d", grid(2, 2, "pitch_x", "pitch_y"), offset="thickness"))


def b20() -> Json:
    ps = params(length=60, width=30, thickness=8, eye_d=12, hole_d=6.6, hole_gap=15, edge=10)
    outline = [rect("length - width / 2", "width", ("(length - width / 2) / 2", 0)), circle("width", ("length - width / 2", 0))]
    return plate(
        "Lifting lug",
        ps,
        outline,
        hole("eye", "eye_d", pts(("length - width / 2", 0)), offset="thickness"),
        hole("bolts", "hole_d", pts(("edge", "-hole_gap / 2"), ("edge", "hole_gap / 2")), offset="thickness"),
    )


def b21() -> Json:
    ps = params(od=48, thickness=10, hub_d=20, hub_len=8, bore=8)
    return design(
        "Gear blank",
        ps,
        [sketch("disc", circle("od")), sketch("hub", circle("hub_d"), offset="thickness")],
        [
            extrude("body", "disc", "thickness"),
            extrude("hub", "hub", "hub_len"),
            hole("bore", "bore", pts((0, 0)), offset="thickness + hub_len"),
        ],
    )


def b22() -> Json:
    ps = params(size=50, hole_d=10)
    return design(
        "Cross-drilled cube",
        ps,
        [sketch("face", rect("size", "size"))],
        [
            extrude("body", "face", "size"),
            hole("z_hole", "hole_d", pts((0, 0)), offset="size"),
            hole("y_hole", "hole_d", pts((0, "size / 2")), ref="XZ"),
            hole("x_hole", "hole_d", pts((0, "size / 2")), ref="YZ"),
        ],
    )


def b23() -> Json:
    ps = params(length=160, width=20, thickness=4, hole_d=5.5, hole_count=6, pitch=25)
    return plate("Flat bar", ps, [rect("length", "width")], hole("holes", "hole_d", grid("hole_count", 1, "pitch", 0), offset="thickness"))


def b24() -> Json:
    ps = params(od=140, thickness=16, bore=43.5, bolt_count=4, pcd=100, hole_d=18)
    flange = b04()
    flange.update(title="DN32 PN16 plate flange", params=ps)
    return flange


def b25() -> Json:
    ps = params(size=80, thickness=8, spigot_d=50, spigot_h=5, bore=30, hole_d=6.6, pitch=64)
    return plate(
        "Spigot adapter",
        ps,
        [rect("size", "size")],
        extrude("spigot", "spigot", "spigot_h"),
        hole("bore", "bore", pts((0, 0)), offset="thickness + spigot_h"),
        hole("holes", "hole_d", grid(2, 2, "pitch", "pitch"), offset="thickness"),
        extra=(sketch("spigot", circle("spigot_d"), offset="thickness"),),
    )


def b26() -> Json:
    ps = params(size=150, thickness=3, hole_d=4.5, inset=7.5)
    c, m = "size / 2 - inset", "-(size / 2 - inset)"
    at = pts((c, c), (m, c), (c, m), (m, m), (0, c), (0, m), (c, 0), (m, 0))
    return plate("Square panel", ps, [rect("size", "size")], hole("fixings", "hole_d", at, offset="thickness"))


def b27() -> Json:
    ps = params(od=40, height=15, shaft_d=6, shaft_depth=12, chamfer=1)
    return design(
        "Control knob",
        ps,
        [sketch("disc", circle("od"))],
        [
            extrude("body", "disc", "height"),
            hole("shaft_hole", "shaft_d", pts((0, 0)), ref="body.start", depth="shaft_depth"),
            {"kind": "chamfer", "id": "top_edge", "name": "Top chamfer", "edges": {"normal": "+z", "extreme": "max"}, "length": "chamfer"},
        ],
    )


def b28() -> Json:
    ps = params(od=25, id=21, length=120)
    return design(
        "Thin-walled tube",
        ps,
        [sketch("ring", circle("od"), circle("id", subtract=True))],
        [extrude("body", "ring", "length")],
    )


def b29() -> Json:
    ps = params(leg_a=50, leg_b=50, width=40, thickness=5, gusset=30, gusset_t=5, hole_d=5.5, hole_gap=20)
    gusset = sketch(
        "gusset", poly(("thickness", "thickness"), ("thickness + gusset", "thickness"), ("thickness", "thickness + gusset")), ref="XZ"
    )
    feats = [
        extrude("gusset", "gusset", "gusset_t", extent="symmetric"),
        hole("base_holes", "hole_d", pts((30, "-hole_gap / 2"), (30, "hole_gap / 2")), offset="thickness"),
        hole("upright_holes", "hole_d", pts(("-hole_gap / 2", 30), ("hole_gap / 2", 30)), ref="YZ", offset="thickness"),
    ]
    return angle("Gusseted angle bracket", ps, "leg_b", [gusset], feats)


def b30() -> Json:
    ps = params(length=70, width=50, thickness=5, barrel_d=12, screw_d=3.4, screw_gap=24, corner_d=4.5, pitch_x=60, pitch_y=40)
    return plate(
        "Sensor mounting plate",
        ps,
        [rect("length", "width")],
        hole("barrel", "barrel_d", pts((0, 0)), offset="thickness"),
        hole("sensor_screws", "screw_d", pts(("-screw_gap / 2", 0), ("screw_gap / 2", 0)), offset="thickness"),
        hole("corner_holes", "corner_d", grid(2, 2, "pitch_x", "pitch_y"), offset="thickness"),
    )


CASES: dict[str, Callable[[], Json]] = {
    "b01-cover-plate": b01,
    "b02-round-spacer": b02,
    "b03-square-tube": b03,
    "b04-bolt-disc": b04,
    "b05-shaft-collar": b05,
    "b06-bearing-block": b06,
    "b07-counterbored-plate": b07,
    "b08-unequal-angle": b08,
    "b09-u-channel": b09,
    "b10-stepped-pin": b10,
    "b11-lightened-disc": b11,
    "b12-machine-base": b12,
    "b13-standoff": b13,
    "b14-bearing-housing": b14,
    "b15-nema23-plate": b15,
    "b16-hinge-leaf": b16,
    "b17-cup": b17,
    "b18-m16-washer": b18,
    "b19-window-frame": b19,
    "b20-lifting-lug": b20,
    "b21-gear-blank": b21,
    "b22-cross-drilled-cube": b22,
    "b23-flat-bar": b23,
    "b24-dn32-flange": b24,
    "b25-spigot-adapter": b25,
    "b26-square-panel": b26,
    "b27-control-knob": b27,
    "b28-thin-tube": b28,
    "b29-gusseted-angle": b29,
    "b30-sensor-plate": b30,
}


if __name__ == "__main__":
    for case_id, make in CASES.items():
        (HERE / f"{case_id}.json").write_text(json.dumps(make(), indent=2) + "\n", encoding="utf-8")
