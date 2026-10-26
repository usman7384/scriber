import random
from pathlib import Path

from partwright_agent import FakeLLM
from partwright_training.families import FAMILIES
from partwright_training.paraphrase import Paraphraser, defaults, numbers, requote
from partwright_training.render import render

SLEEVE = "Spacer sleeve, 24 mm outside diameter, 15.2 mm bore, 20 mm long, 0.5 mm chamfer"


def test_numbers_include_words_and_designations() -> None:
    assert numbers("four M6 holes, R3 corners, 0.5 mm chamfer, 120x80") == {4.0, 6.0, 3.0, 0.5, 120.0, 80.0}


def test_rewrites_that_invent_numbers_or_drop_a_thread_size_are_rejected(tmp_path: Path) -> None:
    replies = ["sleeve 24 mm OD, bore 15.2 mm, 25 mm long", "plate with holes", "sleeve 24 mm OD, bore 15.2 mm, 20 mm long"]
    para = Paraphraser(FakeLLM(replies), tmp_path / "c.jsonl")
    assert para.rewrite(SLEEVE, "terse", 0) is None
    assert para.rewrite("plate with four M6 holes", "terse", 1) is None
    assert para.rewrite(SLEEVE, "terse", 2) is not None


def test_cached_rewrites_are_not_asked_again(tmp_path: Path) -> None:
    Paraphraser(FakeLLM(["a small plain sleeve"]), tmp_path / "c.jsonl").vague(SLEEVE, 0)
    assert Paraphraser(FakeLLM([]), tmp_path / "c.jsonl").vague(SLEEVE, 0) == "a small plain sleeve"


def test_vague_rewrites_must_not_contain_numbers(tmp_path: Path) -> None:
    assert Paraphraser(FakeLLM(["a 24 mm sleeve"]), tmp_path / "c.jsonl").vague(SLEEVE, 0) is None


def test_requote_rejects_a_number_that_changed_meaning() -> None:
    spec = FAMILIES["turned"](random.Random(2))
    original = render(spec, random.Random(2), "oneline").text
    assert requote(spec.design, original, original) is not None
    swapped = original.replace("bore", "long") if "bore" in original else original + " bore"
    bores = [p for p in spec.design.params if p.name == "bore_diameter"]
    if bores:
        assert requote(spec.design, original, swapped) is None


def test_requoted_parameters_quote_the_new_wording() -> None:
    spec = FAMILIES["plate"](random.Random(1))
    original = render(spec, random.Random(1), "oneline").text
    design = requote(spec.design, original, original.upper().lower())
    assert design is not None
    assert all(p.provenance.quote and p.provenance.quote.lower() in original.lower() for p in design.params)


def test_vague_targets_cite_defaults() -> None:
    spec = FAMILIES["block"](random.Random(0))
    assert {p.provenance.source for p in defaults(spec.design).params} == {"default"}
