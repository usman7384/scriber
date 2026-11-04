import json
import random
from pathlib import Path

import pytest

from scriber_agent import evaluate
from scriber_geometry import LocalGeometry
from scriber_ir import Design
from scriber_training.families import FAMILIES
from scriber_training.mutate import MUTATIONS, mutate
from scriber_training.samples import target


def _first(name: str) -> tuple[dict[str, object], dict[str, object]]:
    for seed in range(400):
        spec = FAMILIES[list(FAMILIES)[seed % 4]](random.Random(seed))
        good = json.loads(target(spec))
        broken = MUTATIONS[name](json.loads(target(spec)), random.Random(seed))
        if broken is not None:
            return good, broken
    raise AssertionError(f"{name} never applied")


@pytest.mark.parametrize("name", MUTATIONS)
def test_every_mutation_applies_and_changes_the_design(name: str) -> None:
    good, broken = _first(name)
    assert broken != good


@pytest.mark.parametrize("name", ["drop_hole_plane", "revolve_boss", "pattern_before_source", "word_in_number"])
def test_seen_failure_modes_are_reported_without_building(name: str, tmp_path: Path) -> None:
    _, broken = _first(name)

    def no_build(design: Design, out: Path) -> object:
        raise AssertionError("should fail before the kernel")

    problems, _, _, _ = evaluate(json.dumps(broken), Design.model_validate_json, [], no_build, tmp_path)  # type: ignore[arg-type]
    assert problems


def test_truncated_answers_are_not_json() -> None:
    spec = FAMILIES["plate"](random.Random(0))
    rng = random.Random(0)
    outcomes = [mutate(json.loads(target(spec)), rng) for _ in range(200)]
    cut = [raw for o in outcomes if o and o[0] == "truncated" for raw in [o[1]]]
    assert cut
    with pytest.raises(json.JSONDecodeError):
        json.loads(cut[0])


def test_wrong_value_is_caught_by_the_spec_checks(geometry: LocalGeometry, tmp_path: Path) -> None:
    spec = FAMILIES["plate"](random.Random(1))
    design = json.loads(target(spec))
    design["params"][0]["value"] *= 1.5
    problems, _, _, _ = evaluate(json.dumps(design), Design.model_validate_json, list(spec.checks), geometry.build, tmp_path)
    assert any("requirement not met" in p for p in problems)
