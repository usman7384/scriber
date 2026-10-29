from pathlib import Path

from partwright_cli.config import llm_for, load

ROOT = Path(__file__).parents[3]


def test_image_requests_have_their_own_vision_model() -> None:
    config = load(ROOT / "config.yaml")
    assert config.llm.vision == "qwen3.5:4b" != config.llm.default
    assert llm_for(config, config.llm.vision).name == "qwen3.5:4b"
