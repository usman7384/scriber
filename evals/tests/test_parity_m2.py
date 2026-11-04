import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from scriber_agent import FakeLLM
from scriber_cli.config import AgentConfig, Config, EmbeddingsConfig, GeometryConfig, LLMConfig
from scriber_evals.parity import Evidence, Rig
from scriber_evals.parity_m2 import FIXTURES, ROWS, fixture, pocket, spec_holes
from scriber_geometry import LocalGeometry

NONE = json.dumps({"requirements": []})


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry()
    yield g
    g.close()


def run(row: str, tmp_path: Path, geometry: LocalGeometry, *answers: str, max_repairs: int = 3) -> tuple[Evidence, FakeLLM]:
    llm = FakeLLM(list(answers))
    config = Config(
        llm=LLMConfig(host="", default="fake", ci="fake", models={}),
        embeddings=EmbeddingsConfig(model="hash"),
        agent=AgentConfig(max_repairs=max_repairs),
        geometry=GeometryConfig(),
        output_dir=tmp_path,
        data_dir=tmp_path,
    )
    return ROWS[row](Rig(tmp_path, geometry, llm, config)), llm


def doc_id(name: str) -> str:
    return "d" + hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()[:12]


def param(name: str, value: float, unit: str = "mm", ref: str | None = None) -> dict[str, Any]:
    provenance = {"source": "document", "ref": ref} if ref else {"source": "prompt", "quote": ""}
    return {"name": name, "value": value, "unit": unit, "provenance": provenance}


def sketch(sid: str, width: Any, height: Any, offset: Any = 0, **extra: Any) -> dict[str, Any]:
    return {"id": sid, "plane": {"offset": offset}, "entities": [{"kind": "rect", "width": width, "height": height, **extra}]}


def extrude(fid: str, sketch_id: str, distance: Any, **extra: Any) -> dict[str, Any]:
    return {
        "kind": "extrude",
        "id": fid,
        "name": fid.title(),
        "intent": f"{fid} of the part",
        "sketch": sketch_id,
        "distance": distance,
        **extra,
    }


def hole(fid: str, top: Any, points: list[list[Any]], **spec: Any) -> dict[str, Any]:
    at = {"kind": "points", "points": points}
    return {"kind": "hole", "id": fid, "name": fid.title(), "intent": f"{fid} holes", "plane": {"offset": top}, "at": at, **spec}


def design(title: str, sketches: list[dict[str, Any]], features: list[dict[str, Any]], params: list[dict[str, Any]] | None = None) -> str:
    part = {"id": "part", "name": title, "sketches": sketches, "features": features}
    return json.dumps({"title": title, "params": params or [], "parts": [part]})


def spec_plate(shift: float = 0.0) -> str:
    points = [[x - 100 + shift, y - 60] for x, y in spec_holes()]
    return design("Spec plate", [sketch("s", 200, 120)], [extrude("plate", "s", 5), hole("spec", 5, points, diameter=6.6)])


def sensor_plate() -> str:
    params = [param("size", 150), param("thickness", 8), param("bore_d", 82, ref=f"{doc_id('requirements.pdf')}#p1:l3")]
    params.append(param("hole_count", 4, ""))
    mount = {**hole("mount", "thickness", []), "at": {"kind": "polar", "count": "hole_count", "diameter": 120}, "fastener": "M6"}
    features = [extrude("plate", "s", "thickness"), hole("bore", "thickness", [[0, 0]], diameter="bore_d"), mount]
    return design("Sensor plate", [sketch("s", "size", "size")], features, params)


def edge_plate(dx: float, dy: float) -> str:
    points = [[sx * dx, sy * dy] for sx in (-1, 1) for sy in (-1, 1)]
    return design("Edge plate", [sketch("s", 100, 60)], [extrude("plate", "s", 5), hole("d10", 5, points, diameter=10)])


def box(wall: float, size: tuple[float, float, float], wall_ref: str | None = None, bosses: bool = False) -> str:
    length, width, height = size
    shell = {"kind": "shell", "id": "shell", "name": "Shell", "thickness": "wall", "open": [{"normal": "+z", "extreme": "max"}]}
    features = [extrude("body", "s", height), shell]
    sketches = [sketch("s", length, width)]
    if bosses:
        corners = [[sx * (length / 2 - 10), sy * (width / 2 - 10)] for sx in (-1, 1) for sy in (-1, 1)]
        circles = [{"kind": "circle", "center": c, "diameter": 8} for c in corners]
        sketches.append({"id": "b", "plane": {"offset": wall}, "entities": circles})
        features += [extrude("bosses", "b", 10), hole("insert", wall + 10, corners, diameter=4.0, depth=8)]
    return design("Electronics box", sketches, features, [param("wall", wall, ref=wall_ref)])


def mounting_plate(dowels: bool = True) -> str:
    features = [extrude("plate", "s", 8), hole("bore", 8, [[0, 0]], diameter=40), hole("sensor", 8, [[45, 0]], diameter=25)]
    features += [hole("m6", 8, [[x, y] for x in (-85, 85) for y in (-45, 45)], fastener="M6")]
    features += [hole("m4", 8, [[x, y] for x in (-30, 30) for y in (-45, 45)], fastener="M4")]
    features += [hole("m10", 8, [[-80, 0], [80, 0]], fastener="M10")]
    features += [hole("vent", 8, [[x, y] for x in (-15, 0, 15) for y in (-40, 40)], diameter=3)]
    if dowels:
        features.append(hole("dowel", 8, [[-50, -30], [-50, 30]], diameter=8))
    return design("Mounting plate", [sketch("s", 200, 120)], features)


def refined(d: Any) -> str:
    return json.dumps({"updates": [], "design": json.loads(d.model_dump_json())})


def test_in_2_plate_from_markdown_spec(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, llm = run("IN-2", tmp_path, geometry, NONE, spec_plate())
    assert ev.passed, ev
    assert ev.measured["max_centre_error_mm"] == 0.0
    assert "hole_h10 = 6.6mm at x=180, y=105" in llm.calls[1][-1].content


def test_in_2_misplaced_holes_fail(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run("IN-2", tmp_path, geometry, NONE, spec_plate(shift=0.2), max_repairs=0)
    assert not ev.passed and ev.measured["max_centre_error_mm"] == pytest.approx(0.2)


def test_in_3_csv_and_xlsx_give_identical_models(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, llm = run("IN-3", tmp_path, geometry, NONE, spec_plate(), NONE, spec_plate())
    assert ev.passed, ev
    assert all("hole_h10" in llm.calls[i][-1].content for i in (1, 3))


def test_in_9_uploaded_step_made_longer(tmp_path: Path, geometry: LocalGeometry) -> None:
    longer = json.loads(fixture("bracket").model_dump_json())
    for p in longer["params"]:
        p["provenance"] = {"source": "default"}
    longer["params"][0] |= {"value": 96, "provenance": {"source": "prompt", "quote": "20 % longer"}}
    ev, llm = run("IN-9", tmp_path, geometry, NONE, json.dumps(longer))
    assert ev.passed, ev
    assert "similar uploaded part bracket.step: overall 5 x 40 x 80 mm" in llm.calls[1][-1].content


@pytest.mark.parametrize("row", ["IN-12", "DP-17"])
def test_requirements_pdf_drives_holes_bore_and_trace(row: str, tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run(row, tmp_path, geometry, NONE, sensor_plate())
    assert ev.passed, ev
    assert ev.measured["req_2_features"] == "part/part/bore"


def test_in_13_rule_document_moves_holes_off_the_edge(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, llm = run("IN-13", tmp_path, geometry, NONE, edge_plate(42, 22), edge_plate(35, 15))
    assert ev.passed, ev
    assert ev.measured["repairs"] == 1
    assert "min_hole_edge_ratio" in llm.calls[-1][-1].content


def test_in_13_unrepaired_plate_fails(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run("IN-13", tmp_path, geometry, NONE, edge_plate(42, 22), max_repairs=0)
    assert not ev.passed and ev.measured == {"built": False}


def test_in_15_wall_from_report(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run("IN-15", tmp_path, geometry, NONE, box(3.2, (100, 70, 40), f"{doc_id('report.pdf')}#p2:l1"))
    assert ev.passed, ev


def test_cx_4_graph_links_kmm28_m3_and_the_part(tmp_path: Path, geometry: LocalGeometry) -> None:
    holes = [[x, y] for x in (-22, 22) for y in (-12, 12)]
    mount = design(
        "KMM-28 motor mount", [sketch("s", 60, 40)], [extrude("plate", "s", 4), {**hole("m3", 4, holes, fastener="M3"), "name": "M3 holes"}]
    )
    ev, _ = run("CX-4", tmp_path, geometry, NONE, mount)
    assert ev.passed, ev


def test_cx_7_every_spec_constraint_is_evaluated_and_failures_repaired(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, llm = run("CX-7", tmp_path, geometry, NONE, mounting_plate(dowels=False), mounting_plate())
    assert ev.passed, ev
    assert (ev.measured["evaluated"], ev.measured["passed"], ev.measured["repairs"]) == (10, 10, 1)
    assert "REQ-4: 2 x Ø8 dowel holes" in llm.calls[-1][-1].content


def test_cx_8_conventions_shape_the_box(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, llm = run("CX-8", tmp_path, geometry, NONE, box(2.5, (80, 60, 30), bosses=True))
    assert ev.passed, ev
    assert "Team conventions" in llm.calls[1][-1].content and "Bosses: 4×M3" in llm.calls[1][-1].content  # noqa: RUF001


def test_cx_9_typed_facts(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run("CX-9", tmp_path, geometry)
    assert ev.passed, ev


def test_cx_10_intent_and_provenance_survive_a_byte_identical_round_trip(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run("CX-10", tmp_path, geometry, NONE, sensor_plate())
    assert ev.passed, ev
    assert ev.measured["params_citing_documents"] == 1


def test_cx_11_changed_requirement_marks_its_model_stale(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run("CX-11", tmp_path, geometry, NONE, sensor_plate())
    assert ev.passed, ev
    assert ev.measured["req_3_features"] == "plate/part/bore, plate/part/mount, plate/part/plate"


@pytest.mark.parametrize("row", ["VM-1", "VM-3", "VM-5", "CD-8"])
def test_rows_without_a_model(row: str, tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run(row, tmp_path, geometry)
    assert ev.passed, ev


def test_vm_2_milling_fillets_the_pocket(tmp_path: Path, geometry: LocalGeometry) -> None:
    ev, _ = run("VM-2", tmp_path, geometry, NONE, refined(pocket(3)))
    assert ev.passed, ev
    assert ev.measured["corner_radii"] == "3.000 x 3.000 x 3.000 x 3.000"


def test_vm_2_removing_the_pocket_is_not_a_fix(tmp_path: Path, geometry: LocalGeometry) -> None:
    block = pocket(0).parts[0]
    solid = pocket(0).model_copy(
        update={"parts": [block.model_copy(update={"sketches": block.sketches[:1], "features": block.features[:1]})]}
    )
    ev, _ = run("VM-2", tmp_path, geometry, NONE, refined(solid))
    assert not ev.passed and ev.measured["milling_after"] is True


def test_cd_5_switching_fdm_to_milling_reshapes_and_reports(tmp_path: Path, geometry: LocalGeometry) -> None:
    milled = json.loads(fixture("bracket-fdm").model_dump_json())
    milled["parts"][0]["sketches"][1]["entities"][0]["corner_radius"] = 3
    milled["parts"][0]["process"] = "milling_3axis"
    ev, _ = run("CD-5", tmp_path, geometry, NONE, json.dumps({"updates": [], "design": milled}))
    assert ev.passed, ev
    assert (tmp_path / "diff.md").exists() and ev.measured["diff_features"] == "bracket.pocket"


def test_vm_7_coverage_gate_fails_on_an_unevaluated_constraint(tmp_path: Path, geometry: LocalGeometry) -> None:
    lid = design("Lid", [sketch("s", 120, 80)], [extrude("lid", "s", 3)])
    ev, _ = run("VM-7", tmp_path, geometry, NONE, mounting_plate(), NONE, sensor_plate(), NONE, lid)
    assert ev.passed, ev
    assert ev.measured["mounting-plate"] == "10/10 evaluated"
    assert ev.measured["sensor-plate"] == "5/5 evaluated"
    assert ev.measured["lid"] == "3/4 evaluated, unevaluated: wall_thickness"
