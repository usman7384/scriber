import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from partwright_context import HashEmbedder, LocalContext, derived_from, to_networkx
from partwright_ir import Design, Rule, ShapeDescriptor

WritePdf = Callable[[str, list[list[str]], list[list[str]] | None], Path]
REQUIREMENTS = ["Requirements", "REQ-1: mount 4×M6", "REQ-2: bore Ø82 ±0.2 mm", "REQ-3: plate thickness 8 mm"]  # noqa: RUF001


def plate(title: str, thickness_ref: str | None = None, bore_ref: str | None = None) -> Design:
    def param(name: str, value: float, unit: str, ref: str | None = None) -> dict[str, Any]:
        provenance = {"source": "document", "ref": ref} if ref else {"source": "prompt"}
        return {"name": name, "value": value, "unit": unit, "provenance": provenance}

    return Design.model_validate(
        {
            "title": title,
            "params": [
                param("thickness", 8, "mm", thickness_ref),
                param("bore_diameter", 82, "mm", bore_ref),
                param("hole_count", 4, ""),
                param("length", 150, "mm"),
            ],
            "parts": [
                {
                    "id": "plate",
                    "name": title,
                    "sketches": [{"id": "outline", "entities": [{"kind": "rect", "width": "length", "height": "length"}]}],
                    "features": [
                        {"kind": "extrude", "id": "body", "name": "Body", "sketch": "outline", "distance": "thickness"},
                        {
                            "kind": "hole",
                            "id": "bore",
                            "name": "Bore",
                            "plane": {"offset": 0},
                            "at": {"kind": "points", "points": [[0, 0]]},
                            "diameter": "bore_diameter",
                        },
                        {
                            "kind": "hole",
                            "id": "mount",
                            "name": "M6 mounting holes",
                            "plane": {"offset": 0},
                            "at": {"kind": "polar", "count": "hole_count", "diameter": 120},
                            "diameter": 6.6,
                        },
                    ],
                }
            ],
        }
    )


def test_six_file_types_are_listed_as_processed(ctx: LocalContext, fixtures: Path, write_pdf: WritePdf, tmp_path: Path) -> None:
    png = tmp_path / "photo.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    paths = [write_pdf("requirements.pdf", [REQUIREMENTS], None), fixtures / "bracket.step", fixtures / "plate_spec.md"]
    paths += [fixtures / "kmm_notes.txt", fixtures / "holes.csv", png]
    for path in paths:
        ctx.ingest("p1", path)
    docs = ctx.documents("p1")
    assert [(d.name, d.status) for d in docs] == [(p.name, "processed") for p in paths]
    assert [d.kind for d in docs] == ["pdf", "step", "md", "txt", "csv", "image"]


def test_requirements_are_retrieved_traced_to_features_and_marked_stale(ctx: LocalContext, write_pdf: WritePdf) -> None:
    doc = ctx.ingest("p1", write_pdf("requirements.pdf", [REQUIREMENTS], None))
    facts = {f.name: f for f in ctx.facts("p1")}
    bore, mount, thickness = facts["req_2_bore"], facts["req_1_mount"], facts["req_3_plate_thickness"]
    assert (bore.value, bore.unit, bore.tol, bore.source.ref) == (82.0, "mm", (-0.2, 0.2), f"{doc.id}#p1:l3")
    assert (mount.count, mount.value) == (4, 6.0)

    pack = ctx.retrieve("p1", "bore diameter tolerance", k=3)
    assert pack.chunks[0].doc_id == doc.id
    assert bore.id in [f.id for f in pack.facts]

    ctx.record_generation("p1", "m1", plate("Bore plate", thickness.id, bore.source.ref), [doc.id])
    ctx.record_generation("p1", "m2", plate("Unrelated plate"), [])
    g = to_networkx(ctx.graph("p1"))

    def features(fact_id: str) -> set[str]:
        return {n for n in derived_from(g, fact_id) if g.nodes[n]["type"] == "feature"}

    assert features(thickness.id) == {"m1/plate/body"}
    assert features(bore.id) == {"m1/plate/bore"}
    assert features(mount.id) == {"m1/plate/mount"}
    assert ctx.stale("p1", [thickness.id]) == ["m1"]
    assert ctx.stale("p1", ["no-such-fact"]) == []


def test_rule_documents_feed_rules_and_retrieval(ctx: LocalContext, fixtures: Path) -> None:
    doc = ctx.ingest("p1", fixtures / "screw-design-norm.md")
    rules = {r.id: r for r in ctx.rules("p1").rules}
    edge = rules["min_hole_edge_ratio"]
    assert (edge.value, edge.binding, edge.source.source, edge.source.ref) == (1.5, "static", "document", f"{doc.id}#p1:l3")
    assert rules["min_wall_thickness"].value == 2.0
    assert rules["min_internal_corner_radius@milling_3axis"].value == 3.0
    assert rules["max_overhang_angle@fdm"].source.source == "document"
    assert (rules["min_hole_diameter"].value, rules["min_hole_diameter"].binding) == (2.5, "dynamic")
    assert rules["max_overall_size"].value == 250.0
    assert "min_hole_edge_ratio" in [r.id for r in ctx.retrieve("p1", "hole to edge distance", k=2).rules]


def test_rule_overrides_are_per_project(ctx: LocalContext, fixtures: Path) -> None:
    ctx.ingest("aero", fixtures / "strict-edge-rule.md")

    def flags(project: str, edge: float, diameter: float) -> bool:
        rule = next(r for r in ctx.rules(project).rules if r.id == "min_hole_edge_ratio")
        return edge / diameter < rule.value

    assert flags("aero", 18, 10)
    assert not flags("default", 18, 10)
    ctx.set_rule("default", Rule(id="min_hole_edge_ratio", kind="min_hole_edge_ratio", value=1.9, unit=""))
    assert flags("default", 18, 10)
    assert len(ctx.rules("default").rules) == len(ctx.rules("aero").rules)


def test_report_values_are_cited(ctx: LocalContext, write_pdf: WritePdf) -> None:
    doc = ctx.ingest("p1", write_pdf("report.pdf", [["Sizing report", "Load case 1"], ["Computed wall thickness 3.2 mm"]], None))
    pack = ctx.retrieve("p1", "enclosure wall thickness", k=2)
    [wall] = [f for f in pack.facts if f.name == "computed_wall_thickness"]
    assert (wall.value, wall.unit, wall.source.ref) == (3.2, "mm", f"{doc.id}#p2:l1")


def test_conventions_join_every_pack(ctx: LocalContext, fixtures: Path) -> None:
    ctx.ingest("p1", fixtures / "Box_Best_Practice.md")
    ctx.ingest("p1", fixtures / "kmm_notes.txt")
    pack = ctx.retrieve("p1", "small electronics box", k=1)
    found = {(f.name, f.value, f.count) for f in pack.conventions}
    assert ("wall_thickness", 2.5, None) in found
    assert ("bosses", 3.0, 4) in found


def test_entities_relations_and_generated_part_links(ctx: LocalContext, fixtures: Path) -> None:
    docs = [ctx.ingest("p1", fixtures / name) for name in ("kmm_overview.md", "kmm_notes.txt", "kmm_bom.csv")]
    edges = {(e.src, e.dst, e.type) for e in ctx.graph("p1").edges}
    assert ("ent:designation:KMM-28", "ent:fastener:M3", "related_to") in edges
    ctx.record_generation("p1", "m1", plate("KMM-28 motor mount"), [docs[0].id, docs[1].id])
    edges = {(e.src, e.dst, e.type) for e in ctx.graph("p1").edges}
    assert ("m1/plate", "ent:designation:KMM-28", "mentions") in edges
    assert ("m1/plate", "ent:fastener:M3", "mentions") in edges
    used_in = {s for s, d, t in edges if t == "used_in" and d == "m1/plate"}
    assert used_in == {docs[0].id, docs[1].id}


def test_stats_follow_the_documented_formula(ctx: LocalContext, fixtures: Path) -> None:
    docs = [ctx.ingest("p1", fixtures / name) for name in ("screw-design-norm.md", "plate_spec.md", "kmm_overview.md")]
    ctx.record_generation("p1", "m1", plate("Plate"), [docs[0].id, docs[1].id, "min_hole_edge_ratio"])
    stats = ctx.stats("p1")
    assert (stats.files, stats.generations, stats.used_in_generation) == (3, 1, 2)
    assert stats.rules == 6
    assert stats.score == 10 * stats.files + 2 * stats.facts + 5 * stats.rules + 20 * stats.used_in_generation
    assert stats.level == math.isqrt(stats.score // 100)
    assert stats.next_level_score == 100 * (stats.level + 1) ** 2


def test_hole_tables_from_markdown_csv_and_xlsx_agree(ctx: LocalContext, fixtures: Path, holes_xlsx: Path) -> None:
    def holes(path: Path) -> list[tuple[str, float | str, tuple[float, float] | None]]:
        doc = ctx.ingest("p1", path)
        return [(f.name, f.value, f.at) for f in ctx.facts("p1", doc.id) if f.kind == "hole"]

    from_md, from_csv, from_xlsx = holes(fixtures / "plate_spec.md"), holes(fixtures / "holes.csv"), holes(holes_xlsx)
    assert len(from_md) == 10
    assert from_md[0] == ("hole_h1", 6.6, (20.0, 15.0))
    assert sorted(from_md) == sorted(from_csv) == sorted(from_xlsx)


def test_similar_parts_rank_uploaded_cad_by_shape(ctx: LocalContext, fixtures: Path, shape: ShapeDescriptor) -> None:
    doc = ctx.ingest("p1", fixtures / "bracket.step")
    box = ShapeDescriptor(bbox_sorted=(40, 300, 300), volume=3_000_000, area=200_000)
    ctx.record_generation("p1", "m1", plate("Big box"), [], shapes={"plate": box})
    longer = shape.model_copy(update={"bbox_sorted": (5, 60, 96)})
    [first, second] = ctx.retrieve("p1", "bracket", k=2, shape=longer).similar_parts
    assert (first.origin, first.doc_id, first.descriptor) == ("uploaded", doc.id, shape)
    assert (second.origin, second.model_id) == ("generated", "m1")
    assert second.design is not None and second.design.title == "Big box"


def test_delete_document_removes_its_records(ctx: LocalContext, fixtures: Path) -> None:
    keep = ctx.ingest("p1", fixtures / "kmm_notes.txt")
    gone = ctx.ingest("p1", fixtures / "kmm_overview.md")
    ctx.delete_document("p1", gone.id)
    assert [d.id for d in ctx.documents("p1")] == [keep.id]
    assert {f.doc_id for f in ctx.facts("p1")} == {keep.id}
    assert all(c.doc_id == keep.id for c in ctx.retrieve("p1", "motor mount screws", k=5).chunks)
    assert not any(n.doc_id == gone.id for n in ctx.graph("p1").nodes)
    assert "ent:fastener:M3" not in {n.id for n in ctx.graph("p1").nodes}
    with pytest.raises(KeyError):
        ctx.delete_document("p1", gone.id)


def test_reingesting_the_same_file_is_idempotent(ctx: LocalContext, fixtures: Path) -> None:
    first = ctx.ingest("p1", fixtures / "plate_spec.md")
    before = ctx.graph("p1").counts
    assert ctx.ingest("p1", fixtures / "plate_spec.md") == first
    assert ctx.graph("p1").counts == before
    assert len(ctx.documents("p1")) == 1


def test_project_files_are_bound_to_their_embedder(tmp_path: Path, fixtures: Path) -> None:
    with LocalContext(tmp_path, HashEmbedder(64)) as ctx:
        ctx.ingest("p1", fixtures / "kmm_notes.txt")
    with LocalContext(tmp_path, HashEmbedder(32)) as other, pytest.raises(ValueError, match="embedder"):
        other.documents("p1")
    with LocalContext(tmp_path, HashEmbedder(64)) as ctx, pytest.raises(ValueError, match="project id"):
        ctx.documents("../escape")


def test_default_rules_can_be_cited_and_unknown_ids_fail(ctx: LocalContext) -> None:
    ctx.record_generation("p1", "m1", plate("Plate"), ["max_overhang_angle@fdm"])
    assert ("default:max_overhang_angle@fdm", "m1/plate", "constrains") in {(e.src, e.dst, e.type) for e in ctx.graph("p1").edges}
    with pytest.raises(KeyError, match="nope"):
        ctx.record_generation("p1", "m2", plate("Plate"), ["nope"])
