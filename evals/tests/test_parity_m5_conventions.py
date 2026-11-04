import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest

from scriber_agent import LLM, FakeLLM
from scriber_cli.config import Config, load
from scriber_evals import parity_m5_conventions
from scriber_evals.parity import Rig, run_row
from scriber_evals.parity_m5_conventions import BASE_ENV, CASES, ROWS, gate, load_cases
from scriber_geometry import LocalGeometry

ROOT = Path(__file__).parents[2]
NO_REQS = json.dumps({"requirements": []})
Json = dict[str, Any]
SMALL = """
- id: box
  prompt: Open-top box 100 x 60 x 30 mm with four screw bosses for a lid.
  conventions: [wall, insert, fillet, edge, names]
  holes: 4
- id: plate
  prompt: Plate 100 x 60 mm, 10 mm thick, a screw hole in each corner.
  conventions: [insert, fillet, edge, names]
  holes: 4
"""


def design(title: str, params: Mapping[str, float], sketches: list[Json], features: list[Json]) -> str:
    ps = [{"name": n, "value": v, "unit": "mm"} for n, v in params.items()]
    return json.dumps({"title": title, "params": ps, "parts": [{"id": "part", "name": title, "sketches": sketches, "features": features}]})


def rect(sid: str, w: str, h: str) -> Json:
    return {"id": sid, "entities": [{"kind": "rect", "width": w, "height": h}]}


def extrude(fid: str, sketch: str, distance: str) -> Json:
    return {"kind": "extrude", "id": fid, "name": fid, "sketch": sketch, "distance": distance}


def grid(sx: str, sy: str) -> Json:
    return {"kind": "grid", "count_x": 2, "count_y": 2, "spacing_x": sx, "spacing_y": sy}


def holes(top: str | float, d: str, at: Json, depth: str | None = None) -> Json:
    h = {"kind": "hole", "id": "holes", "name": "holes", "plane": {"ref": "XY", "offset": top}, "at": at, "diameter": d}
    return h | ({"depth": depth} if depth else {})


def shell(t: str) -> Json:
    return {"kind": "shell", "id": "hollow", "name": "hollow", "thickness": t, "open": [{"normal": "+z", "extreme": "max"}]}


FILLET = {"kind": "fillet", "id": "edges", "name": "edges", "edges": {"parallel": "z"}, "radius": "edge_fillet_mm"}
HOUSE = {"edge_fillet_mm": 1, "insert_bore_mm": 4, "insert_depth_mm": 6, "hole_edge_mm": 8}
INSERTS = grid("length_mm - 2 * hole_edge_mm", "width_mm - 2 * hole_edge_mm")


def house_box() -> str:
    params = {"length_mm": 100, "width_mm": 60, "height_mm": 30, "wall_mm": 2.5, "boss_diameter_mm": 13, **HOUSE}
    x, y = "(length_mm / 2 - hole_edge_mm)", "(width_mm / 2 - hole_edge_mm)"
    circles = [{"kind": "circle", "center": [sx + x, sy + y], "diameter": "boss_diameter_mm"} for sx in ("", "-") for sy in ("", "-")]
    bosses = {"id": "bosses", "plane": {"ref": "XY", "offset": "wall_mm"}, "entities": circles}
    body = [extrude("body", "outline", "height_mm"), FILLET, shell("wall_mm"), extrude("boss", "bosses", "height_mm - wall_mm")]
    bores = holes("height_mm", "insert_bore_mm", INSERTS, "insert_depth_mm")
    return design("Box", params, [rect("outline", "length_mm", "width_mm"), bosses], [*body, bores])


def house_plate() -> str:
    params = {"length_mm": 100, "width_mm": 60, "thickness_mm": 10, **HOUSE}
    features = [extrude("plate", "outline", "thickness_mm"), FILLET, holes("thickness_mm", "insert_bore_mm", INSERTS, "insert_depth_mm")]
    return design("Plate", params, [rect("outline", "length_mm", "width_mm")], features)


def plain_box() -> str:
    params = {"length": 100, "width": 60, "height": 30, "wall": 2, "hole_d": 3.4, "margin": 6}
    floor = holes(0, "hole_d", grid("length - 2 * margin", "width - 2 * margin"))
    return design("Box", params, [rect("outline", "length", "width")], [extrude("body", "outline", "height"), shell("wall"), floor])


def plain_plate() -> str:
    params = {"length": 100, "width": 60, "thickness": 10, "hole_d": 3.4, "margin": 6}
    corners = holes("thickness", "hole_d", grid("length - 2 * margin", "width - 2 * margin"))
    return design("Plate", params, [rect("outline", "length", "width")], [extrude("plate", "outline", "thickness"), corners])


def scripted(box: str, plate: str) -> FakeLLM:
    return FakeLLM([NO_REQS, box, NO_REQS, plate])


def house() -> FakeLLM:
    return scripted(house_box(), house_plate())


def plain() -> FakeLLM:
    return scripted(plain_box(), plain_plate())


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry(timeout_s=120)
    yield g
    g.close()


@pytest.fixture
def small(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cases = tmp_path / "conventions.yaml"
    cases.write_text(SMALL, encoding="utf-8")
    monkeypatch.setattr(parity_m5_conventions, "CASES", cases)


def rig(out: Path, geometry: LocalGeometry, llm: LLM) -> Rig:
    return Rig(out, geometry, llm, load(ROOT / "config.yaml"))


@pytest.mark.usefixtures("small")
def test_house_style_candidate_beats_plain_base(geometry: LocalGeometry, tmp_path: Path) -> None:
    candidate, base = house(), plain()
    ev = gate(rig(tmp_path, geometry, candidate), base)
    assert ev.passed, ev
    assert (ev.measured["candidate_score"], ev.measured["base_score"], ev.measured["gain"]) == (100.0, 0.0, 100.0)
    assert candidate.responses == [] and base.responses == []
    scores = json.loads((tmp_path / "scores.json").read_text(encoding="utf-8"))
    assert scores["candidate"][0]["followed"] == dict.fromkeys(("wall", "insert", "fillet", "edge", "names"), True)
    assert not any(scores["base"][1]["followed"].values())
    assert all(c["built"] for c in scores["candidate"] + scores["base"])


@pytest.mark.usefixtures("small")
@pytest.mark.parametrize(("candidate", "base"), [(plain, house), (house, house)])
def test_gate_needs_a_ten_point_gain(candidate: Any, base: Any, geometry: LocalGeometry, tmp_path: Path) -> None:
    ev = gate(rig(tmp_path, geometry, candidate()), base())
    gain = ev.measured["gain"]
    assert not ev.passed and isinstance(gain, float) and gain < 10, ev


@pytest.mark.usefixtures("small")
def test_cx13_takes_the_base_model_from_the_environment(geometry: LocalGeometry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    named: list[str | None] = []

    def base(config: Config, name: str | None) -> LLM:
        named.append(name)
        return plain()

    monkeypatch.setenv(BASE_ENV, "my-base:0.8b")
    monkeypatch.setattr(parity_m5_conventions, "llm_for", base)
    ev = run_row("CX-13", ROWS["CX-13"], rig(tmp_path, geometry, house()))
    assert ev.passed and named == ["my-base:0.8b"], ev


def test_benchmark_cases_never_state_the_house_style() -> None:
    cases = load_cases(CASES)
    assert len(cases) == 20 and len({c.id for c in cases}) == 20
    assert {c for case in cases for c in case.conventions} == {"wall", "insert", "fillet", "edge", "names"}
    stated = re.compile(r"2\.5|\b4(\.0)? ?mm|\b1 ?mm|\b8 ?mm|insert|fillet|radius|_mm|\N{LATIN CAPITAL LETTER O WITH STROKE}|M3", re.I)
    assert [c.id for c in cases if stated.search(c.prompt)] == []
    assert all((c.holes > 0) == ("insert" in c.conventions) for c in cases)
