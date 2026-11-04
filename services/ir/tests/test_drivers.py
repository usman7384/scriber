from typing import Any

from scriber_ir import Design, FaceDriver, face_driver


def stacked(bracket: Design, **boss: Any) -> Design:
    data = bracket.model_dump()
    part = data["parts"][0]
    part["sketches"].append(
        {"id": "boss_sk", "plane": {"ref": "XY", "offset": "thickness"}, "entities": [{"kind": "circle", "diameter": 20}]}
    )
    part["features"].append({"kind": "extrude", "id": "boss", "name": "Boss", "sketch": "boss_sk", "distance": 8} | boss)
    data["params"].append({"name": "boss_h", "value": 8, "unit": "mm"})
    return Design.model_validate(data)


def test_top_face_of_a_plate_is_driven_by_its_thickness(bracket: Design) -> None:
    assert face_driver(bracket, (12.0, -7.5, 5.0), (0, 0, 1)) == FaceDriver("bracket", "plate", "thickness", 1.0)


def test_bottom_face_and_side_faces_have_no_driver(bracket: Design) -> None:
    assert face_driver(bracket, (0, 0, 0), (0, 0, -1)) is None
    assert face_driver(bracket, (40, 0, 2), (1, 0, 0)) is None


def test_a_face_off_every_cap_plane_has_no_driver(bracket: Design) -> None:
    assert face_driver(bracket, (0, 0, 4.0), (0, 0, 1)) is None


def test_a_stacked_cap_follows_the_plane_offset_and_its_own_distance(bracket: Design) -> None:
    assert face_driver(stacked(bracket), (0, 0, 13), (0, 0, 1)) == FaceDriver("bracket", "boss", "thickness", 1.0)
    assert face_driver(stacked(bracket, distance="boss_h"), (0, 0, 13), (0, 0, 1)) == FaceDriver("bracket", "boss", "boss_h", 1.0)


def test_symmetric_extrude_moves_each_cap_by_half_the_distance(bracket: Design) -> None:
    data = bracket.model_dump()
    data["parts"][0]["features"][0] |= {"extent": "symmetric"}
    design = Design.model_validate(data)
    assert face_driver(design, (0, 0, -2.5), (0, 0, -1)) == FaceDriver("bracket", "plate", "thickness", 0.5)
