from pathlib import Path

import yaml
from pydantic import BaseModel

from partwright_agent import OllamaLLM


class ModelOptions(BaseModel):
    num_ctx: int = 8192
    think: bool | None = None


class LLMConfig(BaseModel):
    host: str
    default: str
    ci: str
    models: dict[str, ModelOptions]


class AgentConfig(BaseModel):
    max_repairs: int = 3
    seed: int = 0


class GeometryConfig(BaseModel):
    timeout_s: float = 120


class Config(BaseModel):
    llm: LLMConfig
    agent: AgentConfig
    geometry: GeometryConfig
    output_dir: Path


def load(path: Path) -> Config:
    return Config.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def llm_for(config: Config, model: str | None) -> OllamaLLM:
    name = model or config.llm.default
    options = config.llm.models.get(name, ModelOptions())
    return OllamaLLM(name, host=config.llm.host, num_ctx=options.num_ctx, think=options.think)
