from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from partwright_geometry import Artifact, BuildError, LocalGeometry
from partwright_ir import Design, validate

BLOCK: dict[str, Any] = {"kind": "extrude", "id": "block", "name": "Block", "sketch": "base", "distance": 20}
BASE: dict[str, Any] = {"id": "base", "entities": [{"kind": "rect", "width": 60, "height": 40}]}


def design(features: Sequence[object], sketches: Sequence[object] = (), datums: Sequence[object] = ()) -> Design:
    part = {"id": "p", "name": "P", "datums": list(datums), "sketches": [BASE, *sketches], "features": [BLOCK, *features]}
    d = Design.model_validate({"ir_version": 2, "title": "v2", "params": [], "parts": [part]})
    assert validate(d) == [], validate(d)
    return d


def build(geometry: LocalGeometry, d: Design, tmp_path: Path) -> Artifact:
    art = geometry.build(d, tmp_path)
    assert art.ok, art.findings
    return art


def holes(art: Artifact) -> list[tuple[float, tuple[int, int, int]]]:
    return sorted((round(h.diameter, 2), tuple(round(abs(c)) for c in h.axis)) for h in art.parts[0].holes)  # type: ignore[misc]


def hole(hid: str, ref: str, **extra: Any) -> dict[str, Any]:
    return {"kind": "hole", "id": hid, "name": hid, "plane": {"ref": ref}, "at": {"kind": "points", "points": [[0, 0]]}, **extra}


def test_boss_on_the_top_face_and_hole_on_its_end(geometry: LocalGeometry, tmp_path: Path) -> None:
    boss = {"id": "boss_sk", "plane": {"ref": "block.top"}, "entities": [{"kind": "circle", "diameter": 20}]}
    feats = [
        {"kind": "extrude", "id": "boss", "name": "Boss", "sketch": "boss_sk", "distance": 8},
        hole("bore", "boss.end", diameter=8, depth=12),
    ]
    art = build(geometry, design(feats, [boss]), tmp_path)
    assert art.parts[0].bbox_size == pytest.approx((60, 40, 28))
    assert holes(art) == [(8.0, (0, 0, 1))]


def test_ports_on_the_front_and_right_faces_drill_inward(geometry: LocalGeometry, tmp_path: Path) -> None:
    feats = [
        hole("front_port", "block.front", diameter=6, depth=15, at={"kind": "points", "points": [[0, 10]]}),
        hole("side_port", "block.right", diameter=5, depth=25, at={"kind": "points", "points": [[0, 10]]}),
    ]
    art = build(geometry, design(feats), tmp_path)
    assert holes(art) == [(5.0, (1, 0, 0)), (6.0, (0, 1, 0))]
    by_axis = {round(abs(h.axis[1])): h for h in art.parts[0].holes}
    assert by_axis[1].center[1] == pytest.approx(-20 + 7.5)


def test_crossing_passages_from_two_faces(geometry: LocalGeometry, tmp_path: Path) -> None:
    feats = [
        hole("down", "block.top", diameter=6, depth=15),
        hole("across", "block.right", diameter=6, depth=30, at={"kind": "points", "points": [[0, 10]]}),
    ]
    art = build(geometry, design(feats), tmp_path)
    assert art.parts[0].solids == 1
    assert len(art.parts[0].holes) >= 1


def test_tilted_datum_cut_makes_an_oblique_face(geometry: LocalGeometry, tmp_path: Path) -> None:
    datum = {"id": "slope", "base": "XY", "offset": 15, "rotate_about": "x", "angle": 30}
    cutter = {"id": "chop", "plane": {"ref": "slope"}, "entities": [{"kind": "rect", "width": 200, "height": 200}]}
    feats = [{"kind": "extrude", "id": "bevel", "name": "Bevel", "sketch": "chop", "mode": "cut", "distance": 50}]
    art = build(geometry, design(feats, [cutter], [datum]), tmp_path)
    removed = 60 * 40 * 20 - art.parts[0].volume
    assert 60 * 0.5 * 20 * (20 - 3.5) * 0.9 < removed < 60 * 40 * 20 * 0.5


def test_concave_selector_rounds_only_pocket_corners(geometry: LocalGeometry, tmp_path: Path) -> None:
    pocket = {"id": "pocket_sk", "plane": {"ref": "block.top"}, "entities": [{"kind": "rect", "width": 30, "height": 20}]}
    cut = {"kind": "extrude", "id": "pocket", "name": "Pocket", "sketch": "pocket_sk", "mode": "cut", "distance": 6}
    sharp = build(geometry, design([cut], [pocket]), tmp_path / "a").parts[0]
    corners = {"kind": "fillet", "id": "r", "name": "R", "edges": {"of": "pocket", "parallel": "z", "convexity": "concave"}, "radius": 3}
    rounded = build(geometry, design([cut, corners], [pocket]), tmp_path / "b").parts[0]
    assert rounded.volume > sharp.volume
    assert rounded.bbox_size == pytest.approx(sharp.bbox_size)


def test_path_with_arc_and_corner_fillet(geometry: LocalGeometry, tmp_path: Path) -> None:
    lug = {
        "kind": "path",
        "start": [-30, -20],
        "segments": [{"to": [30, -20], "fillet": 4}, {"to": [30, 20]}, {"to": [-30, 20], "arc": "ccw", "radius": 40}],
    }
    d = Design.model_validate(
        {
            "title": "lug",
            "params": [],
            "parts": [
                {
                    "id": "p",
                    "name": "P",
                    "sketches": [{"id": "s", "entities": [lug]}],
                    "features": [{"kind": "extrude", "id": "body", "name": "B", "sketch": "s", "distance": 5}],
                }
            ],
        }
    )
    art = build(geometry, d, tmp_path)
    assert art.parts[0].bbox_size[1] > 40


@pytest.mark.parametrize(
    ("extent", "extra", "height"),
    [("symmetric", {"distance": 10}, 10), ("two_sided", {"distance": 6, "distance2": 4}, 10), ("blind", {"distance": -7}, 7)],
)
def test_extrude_extents(extent: str, extra: dict[str, Any], height: float, geometry: LocalGeometry, tmp_path: Path) -> None:
    d = Design.model_validate(
        {
            "title": "e",
            "params": [],
            "parts": [
                {
                    "id": "p",
                    "name": "P",
                    "sketches": [BASE],
                    "features": [{"kind": "extrude", "id": "block", "name": "B", "sketch": "base", "extent": extent, **extra}],
                }
            ],
        }
    )
    assert build(geometry, d, tmp_path).parts[0].bbox_size[2] == pytest.approx(height)


def test_through_all_cut_from_a_face(geometry: LocalGeometry, tmp_path: Path) -> None:
    window = {"id": "w", "plane": {"ref": "block.front"}, "entities": [{"kind": "rect", "center": [0, 10], "width": 20, "height": 8}]}
    cut = {"kind": "extrude", "id": "window", "name": "Window", "sketch": "w", "mode": "cut", "extent": "through_all"}
    art = build(geometry, design([cut], [window]), tmp_path)
    assert art.parts[0].volume == pytest.approx(60 * 40 * 20 - 20 * 8 * 40)


def test_revolve_about_an_offset_axis_makes_a_ring(geometry: LocalGeometry, tmp_path: Path) -> None:
    section = {"id": "s", "plane": {"ref": "XZ"}, "entities": [{"kind": "rect", "center": [25, 0], "width": 4, "height": 4}]}
    ring = {"kind": "revolve", "id": "ring", "name": "Ring", "sketch": "s", "axis": "Y", "axis_offset": 0}
    d = Design.model_validate({"title": "r", "params": [], "parts": [{"id": "p", "name": "P", "sketches": [section], "features": [ring]}]})
    art = build(geometry, d, tmp_path)
    assert art.parts[0].bbox_size[0] == pytest.approx(54)


@pytest.mark.parametrize(
    ("extra", "diameters"),
    [
        ({"fastener": "M6"}, [6.6]),
        ({"fastener": "M6", "fit": "close"}, [6.4]),
        ({"fastener": "M6", "type": "tapped", "depth": 12, "drill_point": "118"}, [5.0]),
        ({"fastener": "M6", "type": "counterbore"}, [6.6, 11.0]),
    ],
)
def test_semantic_holes(extra: dict[str, Any], diameters: list[float], geometry: LocalGeometry, tmp_path: Path) -> None:
    art = build(geometry, design([hole("h", "block.top", **extra)]), tmp_path)
    assert sorted(round(h.diameter, 2) for h in art.parts[0].holes) == diameters


def test_countersink_removes_more_than_the_plain_hole(geometry: LocalGeometry, tmp_path: Path) -> None:
    plain = build(geometry, design([hole("h", "block.top", fastener="M6")]), tmp_path / "a").parts[0]
    sunk = build(geometry, design([hole("h", "block.top", fastener="M6", type="countersink")]), tmp_path / "b").parts[0]
    assert sunk.volume < plain.volume


def test_linear_polar_and_mirror_patterns(geometry: LocalGeometry, tmp_path: Path) -> None:
    rib = {"id": "rib_sk", "plane": {"ref": "block.top"}, "entities": [{"kind": "rect", "center": [-20, 0], "width": 3, "height": 30}]}
    lug = {"id": "lug_sk", "plane": {"ref": "block.top"}, "entities": [{"kind": "circle", "center": [24, 14], "diameter": 6}]}
    feats = [
        {"kind": "extrude", "id": "rib", "name": "Rib", "sketch": "rib_sk", "distance": 5},
        {
            "kind": "pattern",
            "id": "ribs",
            "name": "Ribs",
            "features": ["rib"],
            "type": "linear",
            "direction": "x",
            "count": 3,
            "spacing": 10,
        },
        {"kind": "extrude", "id": "lug", "name": "Lug", "sketch": "lug_sk", "distance": 4},
        {"kind": "pattern", "id": "lugs", "name": "Lugs", "features": ["lug"], "type": "mirror", "mirror_plane": "YZ"},
        hole("pin", "block.bottom", diameter=4, depth=6, at={"kind": "points", "points": [[15, 0]]}),
        {"kind": "pattern", "id": "pins", "name": "Pins", "features": ["pin"], "type": "polar", "axis": "z", "count": 4},
    ]
    art = build(geometry, design(feats, [rib, lug]), tmp_path)
    rib_volume, lug_volume = 3 * 30 * 5, 3.14159 * 9 * 4
    assert art.parts[0].volume > 60 * 40 * 20 + 3 * rib_volume + 2 * lug_volume - 4 * 3.14159 * 4 * 6 - 50
    assert len(art.parts[0].holes) == 4


def test_shell_open_on_two_selected_faces(geometry: LocalGeometry, tmp_path: Path) -> None:
    shell = {
        "kind": "shell",
        "id": "s",
        "name": "S",
        "thickness": 2,
        "open": [{"normal": "+z", "extreme": "max"}, {"normal": "-y", "extreme": "max"}],
    }
    art = build(geometry, design([shell]), tmp_path)
    assert art.parts[0].volume < 60 * 40 * 20 * 0.4


def test_face_reference_to_a_later_feature_is_rejected() -> None:
    d = Design.model_validate(
        {
            "title": "x",
            "params": [],
            "parts": [{"id": "p", "name": "P", "sketches": [BASE], "features": [BLOCK, hole("h", "boss.top", diameter=3)]}],
        }
    )
    assert any("not an earlier feature" in str(e) for e in validate(d))


def test_bad_face_name_and_missing_hole_size_are_reported() -> None:
    d = Design.model_validate(
        {
            "title": "x",
            "params": [],
            "parts": [{"id": "p", "name": "P", "sketches": [BASE], "features": [BLOCK, hole("h", "block.upward")]}],
        }
    )
    errors = " ".join(str(e) for e in validate(d))
    assert "unknown face 'upward'" in errors
    assert "fastener" in errors


def test_cut_from_a_face_that_misses_is_a_kernel_error(geometry: LocalGeometry, tmp_path: Path) -> None:
    away = {"id": "a", "plane": {"ref": "block.top", "offset": 50}, "entities": [{"kind": "rect", "width": 5, "height": 5}]}
    cut = {"kind": "extrude", "id": "miss", "name": "Miss", "sketch": "a", "mode": "cut", "distance": 3}
    with pytest.raises(BuildError) as e:
        geometry.build(design([cut], [away]), tmp_path)
    assert e.value.feature == "miss"
