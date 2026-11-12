from pathlib import Path

import pytest

from scriber_agent import OpenAILLM
from scriber_cli.config import ModelOptions, llm_for, load, tool_path

ROOT = Path(__file__).parents[3]


def test_image_requests_have_their_own_vision_model() -> None:
    config = load(ROOT / "config.yaml")
    assert config.llm.vision == "qwen3.5:4b" != config.llm.default
    assert llm_for(config, config.llm.vision).name == "qwen3.5:4b"


def test_openai_compatible_models_come_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load(ROOT / "config.yaml")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    llm = llm_for(config, "gemini-3.8-flash")
    assert isinstance(llm, OpenAILLM) and llm.url.endswith("/v1beta/openai/chat/completions")
    config.llm.models["broken"] = ModelOptions(provider="openai")
    with pytest.raises(ValueError, match="base_url"):
        llm_for(config, "broken")


def test_tool_paths_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCRIBER_FREECAD", "C:/tools/freecadcmd.exe")
    monkeypatch.setenv("SCRIBER_PRUSASLICER", "")
    assert tool_path("SCRIBER_FREECAD") == Path("C:/tools/freecadcmd.exe")
    assert tool_path("SCRIBER_PRUSASLICER") is None
