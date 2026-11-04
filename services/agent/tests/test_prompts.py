from collections.abc import Iterator
from pathlib import Path

import pytest

from scriber_agent.prompts import EXAMPLES
from scriber_geometry import LocalGeometry
from scriber_ir import Design, validate


@pytest.fixture(scope="module")
def geometry() -> Iterator[LocalGeometry]:
    g = LocalGeometry()
    yield g
    g.close()


@pytest.mark.parametrize(("request_text", "data"), EXAMPLES, ids=[d["title"] for _, d in EXAMPLES])
def test_few_shot_examples_build_valid_parts(request_text: str, data: dict[str, object], geometry: LocalGeometry, tmp_path: Path) -> None:
    design = Design.model_validate(data)
    assert validate(design) == []
    art = geometry.build(design, tmp_path)
    assert art.ok, art.findings
    assert art.parts[0].holes or "hole" not in request_text
