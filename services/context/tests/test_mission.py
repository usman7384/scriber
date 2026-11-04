from pathlib import Path

import pytest

from scriber_context.aircraft import aircraft_design
from scriber_context.mission import ALL, read_mission, size
from scriber_ir import validate

MISSION = """mission:
  name: Survey UAV
  payload:
    mass: {payload}
  endurance: {endurance}
  constraints:
    max_span: 1.2 m
"""


def mission(tmp_path: Path, payload: str = "500 g", endurance: str = "20 min") -> Path:
    path = tmp_path / "mission.yaml"
    path.write_text(MISSION.format(payload=payload, endurance=endurance), encoding="utf-8")
    return path


def test_reads_fields_in_base_units_with_their_source(tmp_path: Path) -> None:
    m = read_mission(mission(tmp_path, payload="0.5 kg"))
    assert (m.payload_g.value, m.endurance_s.value, m.max_span_mm.value) == pytest.approx((500, 1200, 1200))
    assert m.payload_g.provenance.ref == "mission.yaml#payload.mass"
    assert m.payload_g.provenance.quote == "payload.mass: 0.5 kg"


@pytest.mark.parametrize(
    ("payload", "endurance", "message"),
    [("500", "20 min", "payload.mass"), ("500 g", "20 m", "endurance"), ("-5 g", "20 min", "must be positive")],
)
def test_bad_fields_are_named(tmp_path: Path, payload: str, endurance: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        read_mission(mission(tmp_path, payload, endurance))


def test_sizing_matches_the_hand_calculation(tmp_path: Path) -> None:
    sizing = size(read_mission(mission(tmp_path)))
    # V = sqrt(2*50/(1.225*0.5)) = 12.78 m/s; battery share = 9.81*12.78*1200/(10*0.5*120*3600) = 0.0697
    assert sizing.estimates["mtom_g"].value == pytest.approx(500 / (1 - 0.45 - 0.0697), rel=1e-3)
    assert sizing.estimates["battery_wh"].value == pytest.approx(8.70, abs=0.01)
    assert sizing.spec.wing.span.value == pytest.approx(1188)
    assert sizing.spec.wing.root_chord.value == pytest.approx(2 * 204_197 / 1188 / 1.45, rel=1e-3)
    assert sizing.config == "blended_wing_body"


def test_every_param_cites_mission_fields(tmp_path: Path) -> None:
    design = aircraft_design(size(read_mission(mission(tmp_path))).spec)
    assert validate(design) == []
    for p in design.params:
        assert p.provenance.source == "rule" and p.provenance.ref
        source, fields = p.provenance.ref.split("#")
        assert source == "mission.yaml" and set(fields.split(",")) <= set(ALL), p


def test_a_heavy_payload_on_a_short_span_fits_in_the_deep_wing_root(tmp_path: Path) -> None:
    sizing = size(read_mission(mission(tmp_path, payload="2 kg")))
    assert sizing.config == "flying_wing" and sizing.spec.body is None
    assert validate(aircraft_design(sizing.spec)) == []


def test_an_endurance_the_battery_cannot_close_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not close"):
        size(read_mission(mission(tmp_path, endurance="3 h")))
