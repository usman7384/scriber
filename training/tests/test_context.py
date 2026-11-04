import random
from pathlib import Path

from scriber_agent import misquoted
from scriber_geometry import LocalGeometry
from scriber_training.context import edited
from scriber_training.families import FAMILIES
from scriber_training.verify import design_failures


def test_an_edit_changes_one_value_and_keeps_the_rest(geometry: LocalGeometry, tmp_path: Path) -> None:
    built = 0
    for seed in range(12):
        spec = FAMILIES["plate"](random.Random(seed))
        made = edited(spec, random.Random(seed))
        if made is None:
            continue
        prompt, context, design, checks = made
        before, after = spec.design.param_values(), design.param_values()
        changed = [n for n in before if before[n] != after[n]]
        assert len(changed) == 1, changed
        assert misquoted(design, prompt.text) == []
        assert {p.provenance.source for p in design.params if p.name != changed[0]} <= {"user_edit", "default", "standard"}
        assert context.pack.similar_parts[0].design == spec.design
        assert after[changed[0]] in [c.value for c in checks if c.kind == "extent"]
        built += not design_failures(design, checks, spec.exempt, geometry, tmp_path / str(seed))
    assert built >= 3
