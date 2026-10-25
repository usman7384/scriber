import os
from pathlib import Path

import pytest

from partwright_agent import OllamaLLM, generate
from partwright_geometry import LocalGeometry

CI_MODEL = os.environ.get("PARTWRIGHT_CI_MODEL", "qwen3.5:0.8b-q8_0")


@pytest.mark.llm
def test_small_qwen_drives_the_loop_end_to_end(tmp_path: Path) -> None:
    geometry = LocalGeometry()
    try:
        steps = list(
            generate("Rectangular plate 50 x 30 x 4 mm", OllamaLLM(CI_MODEL, num_ctx=8192, think=False), geometry, tmp_path, max_repairs=2)
        )
    finally:
        geometry.close()
    assert steps[0].kind == "requirements"
    assert steps[-1].kind in {"done", "failed"}
    assert steps[-1].result is not None and steps[-1].result.design is not None
