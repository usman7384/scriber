import random
from pathlib import Path

import pytest

from partwright_geometry import LocalGeometry
from partwright_ir import drop_unused_params, normalize, validate
from partwright_training.conventions import PLAIN_STYLES
from partwright_training.house import BORE, HOUSE, PROFILE, WALL
from partwright_training.render import render
from partwright_training.verify import failures

SEEDS = range(40)
SUFFIX = {"mm": "_mm", "deg": "_deg", "": "_n"}


@pytest.mark.parametrize("family", HOUSE)
def test_targets_follow_the_house_style_and_cite_it(family: str) -> None:
    for seed in SEEDS:
        spec = HOUSE[family](random.Random(seed))
        assert validate(spec.design) == [], seed
        assert [p.name for p in drop_unused_params(normalize(spec.design)).params] == spec.params(), seed
        assert all(p.name.endswith(SUFFIX[p.unit]) for p in spec.design.params), seed
        rules = {p.name: p for p in spec.design.params if p.provenance.source == "rule"}
        assert rules["edge_fillet_mm"].value == 1 and all((p.provenance.ref or "").startswith(PROFILE) for p in rules.values())
        assert family != "house-enclosure" or rules["wall_mm"].value == WALL
        assert "insert_bore_mm" not in rules or rules["insert_bore_mm"].value == BORE


@pytest.mark.parametrize("family", HOUSE)
def test_requests_never_state_the_house_style(family: str) -> None:
    for seed in SEEDS:
        spec = HOUSE[family](random.Random(seed))
        for style in PLAIN_STYLES:
            text = render(spec, random.Random(seed), style).text
            assert not any(w in text for w in ("2.5", "_mm", "fillet", "insert", "M3")), (seed, text)
            assert all((p.provenance.quote or "") in text for p in spec.design.params), (seed, style)


@pytest.mark.parametrize("family", HOUSE)
def test_house_parts_build_and_meet_their_checks(family: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    assert all(not failures(HOUSE[family](random.Random(s)), geometry, tmp_path / str(s)) for s in range(4))
