import json
import math
import socket
from collections.abc import Iterator, Mapping
from functools import partial
from pathlib import Path
from typing import Any

import pytest

from partwright_agent import FakeLLM
from partwright_cli.config import load
from partwright_evals import parity_m4_vision, parity_m5_parts
from partwright_evals.parity import Demo, Rig, run_row
from partwright_evals.parity_m5_parts import BENCHMARK, FIXTURES, OFFLINE, PARTS, ROWS, bench, offline, part
from partwright_evals.run import load_cases
from partwright_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]
NO_REQS = json.dumps({"requirements": []})
Json = dict[str, Any]


def design(title: str, params: Mapping[str, float], sketches: list[Json], features: list[Json], **extra: Any) -> str:
    ps = [{"name": n, "value": v, "unit": "" if n.endswith("count") else "mm"} for n, v in params.items()]
    return json.dumps(
        {"title": title, "params": ps, "parts": [{"id": "part", "name": title, "sketches": sketches, "features": features}], **extra}
    )


def sketch(sid: str, *entities: Json, ref: str = "XY", offset: Any = 0) -> Json:
    return {"id": sid, "plane": {"ref": ref, "offset": offset}, "entities": list(entities)}


def rect(w: Any, h: Any, at: tuple[Any, Any] = (0, 0), subtract: bool = False) -> Json:
    return {"kind": "rect", "center": list(at), "width": w, "height": h, "subtract": subtract}


def circle(d: Any, at: tuple[Any, Any] = (0, 0)) -> Json:
    return {"kind": "circle", "center": list(at), "diameter": d}


def poly(*points: tuple[Any, Any]) -> Json:
    return {"kind": "polygon", "points": [list(p) for p in points]}


def extrude(fid: str, sk: str, distance: Any, **extra: Any) -> Json:
    return {"kind": "extrude", "id": fid, "name": fid.title(), "sketch": sk, "distance": distance, **extra}


def hole(fid: str, d: Any, at: Json, ref: str = "XY", offset: Any = 0, **extra: Any) -> Json:
    return {"kind": "hole", "id": fid, "name": fid.title(), "plane": {"ref": ref, "offset": offset}, "at": at, "diameter": d, **extra}


def pts(*xy: tuple[Any, Any]) -> Json:
    return {"kind": "points", "points": [list(p) for p in xy]}


def polar(n: Any, d: Any, start: float = 0) -> Json:
    return {"kind": "polar", "count": n, "diameter": d, "start_angle": start}


def grid(sx: Any, sy: Any) -> Json:
    return {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": sx, "spacing_y": sy}


def arm(sx: int, sy: int, reach: float, half: float) -> Json:
    u, n = (sx / math.sqrt(2), sy / math.sqrt(2)), (-sy / math.sqrt(2), sx / math.sqrt(2))
    return poly(*((s * half * n[0] + t * u[0], s * half * n[1] + t * u[1]) for s, t in ((1, 0), (-1, 0), (-1, reach), (1, reach))))


def quad() -> str:
    corners = [(sx, sy) for sx in (1, -1) for sy in (1, -1)]
    pads = [(80 * sx, 80 * sy) for sx, sy in corners]
    motor = [(x + dx, y + dy) for x, y in pads for dx, dy in ((8, 0), (-8, 0), (0, 9.5), (0, -9.5))]
    body = sketch("body", rect(40, 40), *(arm(sx, sy, 113.14, 6) for sx, sy in corners), *(circle(28, p) for p in pads))
    holes = [hole("motor_holes", 3.2, pts(*motor), offset="plate"), hole("fc_holes", 2.2, grid(16, 16), offset="plate")]
    return design("X quad frame", {"plate": 4}, [body], [extrude("body", "body", "plate"), *holes])


def flange(od: float, t: float, n: int, pcd: float, hole_d: float, bore: float, start: float = 0) -> str:
    holes = [hole("bore", "bore", pts((0, 0)), offset="t"), hole("bolts", "hole_d", polar("bolt_count", "pcd", start), offset="t")]
    params = {"od": od, "t": t, "bolt_count": n, "pcd": pcd, "hole_d": hole_d, "bore": bore}
    return design("Flange", params, [sketch("disc", circle("od"))], [extrude("disc", "disc", "t"), *holes])


def tee(stem: float = 10) -> str:
    outline = poly((-30, 40), (30, 40), (30, 20), (stem, 20), (stem, -20), (-stem, -20), (-stem, 20), (-30, 20))
    at = pts((-20, 30), (0, 30), (20, 30), (0, 10), (0, -10))
    return design(
        "Tee plate", {"t": 4, "hole_d": 5.5}, [sketch("s", outline)], [extrude("body", "s", "t"), hole("holes", "hole_d", at, offset="t")]
    )


def hose(hex_collar: bool = True) -> str:
    params = {
        "barb_tip_r": 6.5,
        "barb_r": 8,
        "barb_len": 30,
        "collar_af": 30,
        "collar_len": 10,
        "fitting_d": 26.4,
        "fitting_len": 20,
        "bore": 12,
    }
    profile = poly((0, 0), ("barb_tip_r", 0), ("barb_r", 5), ("barb_r", "barb_len"), (0, "barb_len"))
    r = params["collar_af"] / math.sqrt(3)
    hexagon = poly(*((r * math.cos(math.radians(60 * k)), r * math.sin(math.radians(60 * k))) for k in range(6)))
    sketches = [
        sketch("barb", profile, ref="XZ"),
        sketch("collar", hexagon if hex_collar else circle(2 * r), offset="barb_len"),
        sketch("fitting", circle("fitting_d"), offset="barb_len + collar_len"),
    ]
    features = [
        {"kind": "revolve", "id": "barb", "name": "Barb", "sketch": "barb", "axis": "Y"},
        extrude("collar", "collar", "collar_len"),
        extrude("fitting", "fitting", "fitting_len"),
        hole("bore", "bore", pts((0, 0)), offset="barb_len + collar_len + fitting_len"),
    ]
    return design("Hose connector", params, sketches, features)


def enclosure(clearance: float = 0.2) -> str:
    d: Json = json.loads((ROOT / "evals/parity/m4/assembly/enclosure.json").read_text(encoding="utf-8"))
    values = {"box_length": 250, "box_width": 100, "box_height": 45, "lid_thickness": 5, "boss_inset": 10}
    d["params"] = [p | {"value": values.get(p["name"], p["value"])} for p in d["params"]]
    added = {"clearance": clearance, "lip_depth": 5, "lip_wall": 2, "cb_d": 6, "cb_depth": 3.2}
    d["params"] += [{"name": n, "value": v, "unit": "mm"} for n, v in added.items()]
    lid = next(p for p in d["parts"] if p["id"] == "lid")
    inner = ("box_length - 2 * wall - 2 * clearance", "box_width - 2 * wall - 2 * clearance")
    lip = sketch("lip", rect(*inner), rect(f"{inner[0]} - 2 * lip_wall", f"{inner[1]} - 2 * lip_wall", subtract=True), ref="plate.start")
    lid["sketches"].append(lip)
    seat = next(f for f in lid["features"] if f["id"] == "clearance")
    seat |= {"type": "counterbore", "diameter": 3.4, "cb_diameter": "cb_d", "cb_depth": "cb_depth"}
    lid["features"].append(extrude("lip", "lip", "lip_depth"))
    for c in d["assembly"]["connectors"]:
        if c["id"].startswith("screw_seat"):
            c["origin"][2] = "lid_thickness - cb_depth"
    return json.dumps(d)


def fin_ray() -> str:
    params = {"length": 100, "base_width": 30, "tip_width": 6, "thickness": 20, "flank": 2, "rib_t": 2, "rib_count": 4}
    outer = poly(("-base_width / 2", 0), ("base_width / 2", 0), ("tip_width / 2", "length"), ("-tip_width / 2", "length"))
    inner = poly(
        ("-(base_width / 2 - flank * 1.1)", "flank"), ("base_width / 2 - flank * 1.1", "flank"),
        ("tip_width / 2 - flank * 0.6", "length - flank"), ("-(tip_width / 2 - flank * 0.6)", "length - flank"),
    )  # fmt: skip
    pitch = "length / (rib_count + 1)"
    sketches = [sketch("outer", outer), sketch("inner", inner), sketch("rib", rect("base_width + 10", "rib_t", (0, pitch)))]
    features = [
        extrude("shell", "outer", "thickness"),
        extrude("hollow", "inner", "thickness", mode="cut"),
        extrude("rib", "rib", "thickness"),
        {"kind": "pattern", "id": "ribs", "name": "Ribs", "features": ["rib"], "type": "linear", "count": "rib_count"}
        | {"direction": "y", "spacing": pitch},
        extrude("trim", "outer", "thickness", mode="intersect"),
    ]
    return design("Fin-ray finger", params, sketches, features)


def angle(legs: float, width: float, t: float, hole_d: float, gusset: bool) -> str:
    profile = poly((0, 0), ("legs", 0), ("legs", "t"), ("t", "t"), ("t", "legs"), (0, "legs"))
    sketches = [sketch("profile", profile, ref="XZ")]
    features = [extrude("body", "profile", "width", extent="symmetric")]
    if gusset:
        sketches.append(sketch("gusset", poly(("t", "t"), ("legs * 0.6", "t"), ("t", "legs * 0.6")), ref="XZ"))
        features.append(extrude("gusset", "gusset", "t", extent="symmetric"))
    side = "width / 4" if gusset else 0
    features += [
        hole("base_hole", "hole_d", pts(("legs * 0.6", side)), offset="t"),
        hole("upright_hole", "hole_d", pts((side, "legs * 0.6")), ref="YZ", offset="t"),
    ]
    return design("Angle bracket", {"legs": legs, "width": width, "t": t, "hole_d": hole_d}, sketches, features)


def spigot_flange() -> str:
    sketches = [sketch("plate", rect("size", "size")), sketch("spigot", circle("spigot_d"), offset="t")]
    features = [
        extrude("plate", "plate", "t"),
        extrude("spigot", "spigot", "spigot_h"),
        hole("bore", "bore", pts((0, 0)), offset="t + spigot_h"),
        hole("bolts", "hole_d", polar("bolt_count", "pcd", 45), offset="t"),
    ]
    params = {"size": 90, "t": 10, "spigot_d": 55, "spigot_h": 3, "bore": 30, "bolt_count": 4, "pcd": 70, "hole_d": 9}
    return design("F07 flange", params, sketches, features)


def kmm_28() -> str:
    motor = pts(("-motor_x / 2", 0), ("motor_x / 2", 0), (0, "-motor_y / 2"), (0, "motor_y / 2"))
    features = [
        extrude("plate", "plate", "t"),
        hole("frame_holes", "frame_d", grid("frame_pitch", "frame_pitch"), offset="t"),
        hole("motor_holes", "motor_d", motor, offset="t"),
        hole("centre", "centre_d", pts((0, 0)), offset="t"),
    ]
    params = {"size": 40, "t": 4, "frame_d": 3.4, "frame_pitch": 32, "motor_d": 3.2, "motor_x": 19, "motor_y": 16, "centre_d": 10}
    return design("KMM-28 motor mount", params, [sketch("plate", rect("size", "size"))], features)


def phone_holder() -> str:
    params = {"phone_width": 75, "clearance": 0.5, "wall": 4, "base_t": 5, "depth": 60, "wall_h": 40}
    inner = "(phone_width + clearance)"
    walls = sketch(
        "walls",
        rect("wall", "depth", (f"-({inner} / 2 + wall / 2)", 0)),
        rect("wall", "depth", (f"{inner} / 2 + wall / 2", 0)),
        offset="base_t",
    )
    sketches = [sketch("base", rect(f"{inner} + 2 * wall + 10", "depth")), walls]
    return design("Phone holder", params, sketches, [extrude("base", "base", "base_t"), extrude("walls", "walls", "wall_h")])


def drill_jig() -> str:
    params = {"length": 130, "width": 100, "height": 20, "pocket_l": 110.4, "pocket_w": 80.4, "pocket_d": 6, "guide_d": 8.5}
    sketches = [sketch("block", rect("length", "width")), sketch("pocket", rect("pocket_l", "pocket_w"), ref="block.end")]
    features = [
        extrude("block", "block", "height"),
        extrude("pocket", "pocket", "pocket_d", mode="cut"),
        hole("guides", "guide_d", grid(85, 60), offset="height"),
    ]
    return design("Drill jig", params, sketches, features)


def intake() -> str:
    params = {"length": 80, "width": 60, "height": 50, "duct_d": 40}
    features = [extrude("body", "body", "height"), hole("duct", "duct_d", pts((0, "height / 2")), ref="XZ")]
    return design("Flush intake", params, [sketch("body", rect("length", "width"))], features)


def servo() -> str:
    params = {"body_l": 22.2, "body_w": 11.8, "body_h": 22.7, "tab_l": 32.2, "tab_t": 2.5, "tab_top": 18.4, "hole_d": 2}
    sketches = [
        sketch("b", rect("body_l", "body_w")),
        sketch("t", rect("tab_l", "body_w"), offset="tab_top - tab_t"),
        sketch("s", circle(4.8, (-5.2, 0)), offset="body_h"),
    ]
    features = [
        extrude("body", "b", "body_h"),
        extrude("tabs", "t", "tab_t"),
        extrude("shaft", "s", 4),
        hole("tab_holes", "hole_d", pts((-13.9, 0), (13.9, 0)), offset="tab_top"),
    ]
    return design("Micro servo", params, sketches, features)


def hubbed_flange() -> str:
    params = {"od": 120, "pcd": 90, "bolt_count": 6, "hole_d": 11, "hub_d": 60, "bore_d": 30, "flange_t": 12, "hub_len": 20}
    features = [
        extrude("disc", "d", "flange_t"),
        extrude("hub", "h", "hub_len"),
        hole("bore", "bore_d", pts((0, 0)), offset="flange_t + hub_len"),
        hole("bolts", "hole_d", polar("bolt_count", "pcd"), offset="flange_t"),
    ]
    return design("Flange", params, [sketch("d", circle("od")), sketch("h", circle("hub_d"), offset="flange_t")], features)


def drawn(name: str, v: dict[str, float]) -> str:
    if "od" in v:
        return flange(v["od"], v["thickness"], int(v["bolt_count"]), v["pcd"], v["hole_d"], v["bore"])
    holes = [hole("holes", "hole_d", grid("pitch_x", "pitch_y"), offset="thickness")]
    return design(name, v, [sketch("s", rect("length", "width"))], [extrude("body", "s", "thickness"), *holes])


def reference(case_id: str) -> str:
    return (FIXTURES / "reference" / f"{case_id}.json").read_text(encoding="utf-8")


GLIDER = (ROOT / "evals/parity/m1/glider.json").read_text(encoding="utf-8")
DRONE = (ROOT / "evals/parity/m4/assembly/drone.json").read_text(encoding="utf-8")
ANSWERS: dict[str, list[str]] = {
    "DP-1": [NO_REQS, quad()],
    "DP-3": [NO_REQS, flange(165, 18, 4, 125, 18, 60.3)],
    "DP-4": [NO_REQS, GLIDER, NO_REQS, json.dumps({"updates": [{"name": "length", "value": 450}], "design": None})],
    "DP-6": [NO_REQS, tee()],
    "DP-8": [NO_REQS, hose()],
    "DP-11": [NO_REQS, enclosure()],
    "DP-13": [NO_REQS, fin_ray(), json.dumps({"param": "rib_count", "values": [4, 6, 8]})],
    "DP-14": [NO_REQS, angle(40, 30, 4, 5.5, False), NO_REQS, angle(50, 40, 5, 6.6, True)],
    "DP-15": [NO_REQS, flange(95, 14, 4, 65, 14, 22, 45), NO_REQS, spigot_flange()],
    "DP-16": [NO_REQS, DRONE],
    "DP-18": [NO_REQS, kmm_28()],
    "DP-19": [NO_REQS, phone_holder()],
    "DP-20": [NO_REQS, drill_jig()],
    "DP-22": [NO_REQS, intake()],
}
SUBSETS = {
    "DP-14": ["dp14-equal-angle", "dp14-single-gusset"],
    "DP-15": ["dp15-en-dn15", "dp15-iso5211-f07"],
    "DP-18": ["dp18-kmm-28"],
    "DP-20": ["dp20-drill-jig"],
}
FAMILIES = {"DP-14": parity_m5_parts.dp_14, "DP-15": parity_m5_parts.dp_15, "DP-18": parity_m5_parts.dp_18, "DP-20": parity_m5_parts.dp_20}
MODEL_ROWS = sorted(ANSWERS)


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()


def rig(out: Path, geometry: LocalGeometry, answers: list[str]) -> Rig:
    return Rig(out, geometry, FakeLLM(answers), load(ROOT / "config.yaml"))


def demo(row: str) -> Demo:
    if row in SUBSETS:
        return partial(FAMILIES[row], cases=[part(c) for c in SUBSETS[row]])
    return ROWS[row]


@pytest.mark.parametrize("row", MODEL_ROWS)
def test_m5_part_row_demo_passes(row: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    llm_rig = rig(tmp_path, geometry, ANSWERS[row])
    ev = run_row(row, demo(row), llm_rig)
    assert ev.passed, ev
    assert isinstance(llm_rig.llm, FakeLLM) and llm_rig.llm.responses == [], f"{row} left scripted answers unused"


@pytest.mark.parametrize(
    ("row", "wrong"),
    [("DP-6", tee(stem=11)), ("DP-8", hose(hex_collar=False)), ("DP-11", enclosure(clearance=0.3))],
    ids=["DP-6", "DP-8", "DP-11"],
)
def test_row_geometry_checks_reject_a_near_miss(row: str, wrong: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run_row(row, ROWS[row], rig(tmp_path, geometry, [NO_REQS, wrong]))
    assert ev.measured["valid"] is True and not ev.passed, ev


def test_a_wrong_part_fails_its_row(geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = run_row("DP-3", ROWS["DP-3"], rig(tmp_path, geometry, [NO_REQS, reference("b04-bolt-disc")] + ["{}"] * 6))
    assert not ev.passed and ev.measured["valid"] is True


def test_dp12_gates_the_datasheet_tab_spacing(geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wide = servo().replace("13.9", "14.2")
    for answer, passes in ((servo(), True), (wide, False)):
        vision = FakeLLM([answer])
        monkeypatch.setattr(parity_m4_vision, "vision_llm", lambda rig, v=vision: v)
        ev = run_row("DP-12", ROWS["DP-12"], rig(tmp_path / str(passes), geometry, [NO_REQS]))
        assert ev.passed is passes, ev


def test_ge11_scores_params_read_from_drawings(geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    truth: dict[str, dict[str, float]] = json.loads((FIXTURES / "vision" / "truth.json").read_text(encoding="utf-8"))
    vision = FakeLLM([drawn(n, v) for n, v in truth.items()])
    monkeypatch.setattr(parity_m4_vision, "vision_llm", lambda rig: vision)
    ev = run_row("GE-11", ROWS["GE-11"], rig(tmp_path, geometry, [NO_REQS] * len(truth)))
    assert ev.passed and ev.measured["share"] == 1.0, ev
    assert all(call[-1].images for call in vision.calls)


def test_pf3_times_the_drawing_and_photo_fixtures(geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vision = FakeLLM([servo(), hubbed_flange()])
    monkeypatch.setattr(parity_m4_vision, "vision_llm", lambda rig: vision)
    ev = run_row("PF-3", ROWS["PF-3"], rig(tmp_path, geometry, [NO_REQS, NO_REQS]))
    assert ev.passed and ev.measured["IN-5_passed"] and ev.measured["IN-6_passed"], ev


def test_pf8_reads_ollama_counters(geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parity_m5_parts, "ollama_stats", lambda host, model: (512, 20_000_000_000, 4 * 2**30))
    ev = run_row("PF-8", ROWS["PF-8"], rig(tmp_path, geometry, []))
    assert ev.passed and ev.measured["tokens_per_s"] == 25.6, ev
    monkeypatch.setattr(parity_m5_parts, "ollama_stats", lambda host, model: (512, 80_000_000_000, 4 * 2**30))
    assert not run_row("PF-8", ROWS["PF-8"], rig(tmp_path, geometry, [])).passed


@pytest.fixture(scope="module")
def bench_dir(geometry: LocalGeometry, tmp_path_factory: pytest.TempPathFactory) -> Path:
    run_dir = tmp_path_factory.mktemp("parity")
    answers = [a for c in load_cases(BENCHMARK) for a in (NO_REQS, reference(c.id))]
    (run_dir / "seed").mkdir()
    results = bench(rig(run_dir / "seed", geometry, answers))
    assert all(r.valid and r.checks_passed == r.checks_total for r in results)
    return run_dir


@pytest.mark.parametrize("row", ["GE-8", "VM-8", "PF-1", "PF-7"])
def test_benchmark_rows_read_one_pass(row: str, geometry: LocalGeometry, bench_dir: Path) -> None:
    ev = run_row(row, ROWS[row], rig(bench_dir, geometry, []))
    assert ev.passed, ev


def test_benchmark_scores_reference_parts_as_exact(bench_dir: Path) -> None:
    results = json.loads((bench_dir / "benchmark.json").read_text(encoding="utf-8"))
    assert len(results) == 30
    assert all(r["param_accuracy"] == 1.0 and r["hausdorff_mm"] <= 1e-3 for r in results)


def test_wp15_completes_ten_prompts_offline(geometry: LocalGeometry, tmp_path: Path) -> None:
    answers = [a for c in load_cases(BENCHMARK) if c.id in OFFLINE for a in (NO_REQS, reference(c.id))]
    ev = run_row("WP-15", ROWS["WP-15"], rig(tmp_path, geometry, answers))
    assert ev.passed and ev.measured["completed"] == 10, ev


def test_offline_blocks_anything_but_loopback() -> None:
    with offline() as blocked:
        with pytest.raises(OSError, match="network disabled"):
            socket.create_connection(("192.0.2.1", 80), timeout=1)
        with pytest.raises(OSError, match="network disabled"):
            socket.getaddrinfo("example.com", 443)
    assert blocked == ["192.0.2.1", "example.com"]
    assert socket.getaddrinfo is not None and "guarded" not in socket.getaddrinfo.__name__


def test_case_files_hold_the_m5_specs() -> None:
    parts, benchmark = load_cases(PARTS), load_cases(BENCHMARK)
    ids = [c.id for c in parts + benchmark]
    assert len(ids) == len(set(ids)) == 80
    assert sum(c.id.startswith("dp14-") for c in parts) == 16
    assert sum(c.id.startswith("dp15-") for c in parts) == 16
    assert all((FIXTURES / "reference" / f"{c.id}.json").exists() for c in benchmark)
