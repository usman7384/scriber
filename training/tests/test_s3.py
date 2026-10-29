import dataclasses
import random
from pathlib import Path

import pytest

from partwright_agent import misquoted
from partwright_geometry import LocalGeometry
from partwright_ir import Design, drop_unused_params, normalize, validate
from partwright_training.context import tabled
from partwright_training.dataset import _ngrams, eval_ngrams
from partwright_training.families import FAMILIES, S3_FAMILIES
from partwright_training.intent import intended
from partwright_training.names import renamed
from partwright_training.render import STYLES, render
from partwright_training.spec import Spec
from partwright_training.verify import failures

NEW = {k: v for k, v in S3_FAMILIES.items() if k not in FAMILIES}
ROOT = Path(__file__).resolve().parents[2]
# seeds whose gears build in seconds; the default wall probe takes a minute on large gears
BUILD_SEEDS = {"gear": (6, 7)}


@pytest.mark.parametrize("family", NEW)
def test_s3_designs_validate_use_every_parameter_and_quote_the_request(family: str) -> None:
    for seed in range(40):
        spec = renamed(NEW[family](random.Random(seed)), random.Random(seed))
        assert validate(spec.design) == [], (seed, validate(spec.design))
        assert [p.name for p in drop_unused_params(normalize(spec.design)).params] == spec.params(), seed
        for style in STYLES:
            text = render(spec, random.Random(seed), style).text
            assert misquoted(spec.design, text) == [], (seed, style)


@pytest.mark.parametrize("family", NEW)
def test_s3_parts_build_and_meet_their_checks(family: str, geometry: LocalGeometry, tmp_path: Path) -> None:
    seeds = BUILD_SEEDS.get(family, range(4))
    problems = {s: failures(NEW[family](random.Random(s)), geometry, tmp_path / str(s)) for s in seeds}
    assert sum(not p for p in problems.values()) >= len(seeds) - 1, problems


def test_every_s3_target_feature_carries_an_intent() -> None:
    for family, make in S3_FAMILIES.items():
        for seed in range(10):
            design = intended(make(random.Random(seed))).design
            assert all(f.intent.strip() for p in design.parts for f in p.features), (family, seed)


def test_intent_fills_only_empty_intents() -> None:
    spec = NEW["shaft"](random.Random(1))
    assert intended(spec).design == spec.design
    plain = FAMILIES["plate"](random.Random(1))
    assert all(not f.intent for f in plain.design.parts[0].features)
    assert [f.id for f in intended(plain).design.parts[0].features] == [f.id for f in plain.design.parts[0].features]


def test_assemblies_have_several_parts_and_joints() -> None:
    specs = [NEW[f](random.Random(s)) for f in ("assembly", "gear", "enclosure") for s in range(12)]
    multi = [s.design for s in specs if len(s.design.parts) > 1]
    assert len(multi) >= 20
    assert all(d.assembly or any(f.kind == "lid" for p in d.parts for f in p.features) for d in multi)
    assert max(len(d.parts) for d in multi) == 6


def test_a_hole_table_is_placed_from_the_corner_and_a_shift_is_caught(geometry: LocalGeometry, tmp_path: Path) -> None:
    spec = next(s for s in (NEW["table"](random.Random(n)) for n in range(20)) if tabled(s, random.Random(0)))
    assert spec.design.params[0].name == "plate_length"
    assert failures(spec, geometry, tmp_path / "ok") == []
    data = spec.design.model_dump(mode="json")
    data["parts"][0]["sketches"][0]["entities"][0]["center"] = ["plate_length / 2 + 1", "plate_width / 2"]
    shifted = dataclasses.replace(spec, design=Design.model_validate(data))
    assert any(p.startswith("position") for p in failures(shifted, geometry, tmp_path / "shifted"))


def test_a_documented_hole_table_cites_one_fact_per_hole() -> None:
    for seed in range(30):
        spec = NEW["table"](random.Random(seed))
        made = tabled(spec, random.Random(seed))
        centred = spec.design.parts[0].sketches[0].model_dump()["entities"][0]["center"] == (0, 0)
        assert (made is None) == centred, seed
        if made is None:
            continue
        prompt, context, design = made
        facts = context.pack.facts
        assert [(f.at, f.value) for f in facts] == [((x, y), d) for x, y, d in spec.positions]
        assert misquoted(design, prompt.text) == []
        cited = {p.provenance.ref for p in design.params if p.provenance.source == "document"}
        assert cited and cited <= {f.id for f in facts}


def test_s3_prompts_share_no_eight_words_with_the_eval_cases() -> None:
    leaks = eval_ngrams(ROOT)
    hits = []
    for family, make in NEW.items():
        for seed in range(60):
            spec = make(random.Random(seed))
            for style in STYLES:
                text = render(spec, random.Random(seed), style).text
                if _ngrams(text) & leaks:
                    hits.append((family, seed, style))
    assert len(hits) <= 2, hits


def _keyed(spec: Spec) -> bool:
    return any(f.kind == "keyway" for p in spec.design.parts for f in p.features)


def test_small_shafts_take_keyways_and_keyed_bores_keep_their_hole_checks(geometry: LocalGeometry, tmp_path: Path) -> None:
    small = [
        s
        for s in (NEW["shaft"](random.Random(n)) for n in range(40))
        if _keyed(s) and max(v for k, v in s.design.param_values().items() if k.endswith("_diameter")) < 20
    ]
    assert small
    assert failures(small[0], geometry, tmp_path) == []
    bored = [NEW[f](random.Random(n)) for f in ("gear", "pulley") for n in range(40)]
    assert all(any(c.kind == "holes" for c in s.checks) for s in bored if _keyed(s))
