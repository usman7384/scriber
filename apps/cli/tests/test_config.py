from pathlib import Path

import pytest

from partwright_cli.config import llm_for, load, tool_path

ROOT = Path(__file__).parents[3]


def test_image_requests_have_their_own_vision_model() -> None:
    config = load(ROOT / "config.yaml")
    assert config.llm.vision == "qwen3.5:4b" != config.llm.default
    assert llm_for(config, config.llm.vision).name == "qwen3.5:4b"


def test_tool_paths_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARTWRIGHT_FREECAD", "C:/tools/freecadcmd.exe")
    monkeypatch.setenv("PARTWRIGHT_PRUSASLICER", "")
    assert tool_path("PARTWRIGHT_FREECAD") == Path("C:/tools/freecadcmd.exe")
    assert tool_path("PARTWRIGHT_PRUSASLICER") is None
