import random
from pathlib import Path

import pytest

from partwright_geometry import LocalGeometry
from partwright_ir import drop_unused_params, normalize, validate
from partwright_training.families import FAMILIES
from partwright_training.render import STYLES, render
from partwright_training.verify import failures

SEEDS = range(60)


@pytest.mark.parametrize("family", FAMILIES)
def test_designs_validate_and_use_every_parameter(family: str) -> None:
    for seed in SEEDS:
        spec = FAMILIES[family](random.Random(seed))
        assert validate(spec.design) == [], (seed, validate(spec.design))
        assert [p.name for p in drop_unused_params(normalize(spec.design)).params] == spec.params(), seed


@pytest.mark.parametrize("family", FAMILIES)
def test_every_quote_appears_in_every_prompt_style(family: str) -> None:
    for seed in SEEDS:
        spec = FAMILIES[family](random.Random(seed))
        for style in STYLES:
            text = render(spec, random.Random(seed), style).text
            missing = [p.name for p in spec.design.params if (p.provenance.quote or "") not in text]
            assert not missing, (seed, style, missing)


def test_spec_sheet_lists_the_parameter_names() -> None:
    spec = FAMILIES["block"](random.Random(3))
    prompt = render(spec, random.Random(3), "spec")
    assert prompt.required_params == tuple(spec.params())
    assert all(f"`{n}`" in prompt.text for n in spec.params())


@pytest.mark.parametrize("family", FAMILIES)
def test_generated_parts_build_and_meet_their_checks(family: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    passed = sum(not failures(FAMILIES[family](random.Random(s)), geometry, tmp_path / str(s)) for s in range(6))
    assert passed >= 5
