import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from scriber_agent import LLM, AnthropicLLM, OllamaLLM, OpenAILLM
from scriber_agent.anthropic_llm import Effort


class ModelOptions(BaseModel):
    num_ctx: int = 8192
    think: bool | None = None
    max_tokens: int | None = None
    few_shot: bool = True
    provider: Literal["ollama", "anthropic", "openai"] = "ollama"
    effort: Effort | None = None
    base_url: str | None = None
    api_key_env: str | None = None


class LLMConfig(BaseModel):
    host: str
    default: str
    ci: str
    vision: str = "qwen3.5:4b"
    models: dict[str, ModelOptions]


class AgentConfig(BaseModel):
    max_repairs: int = 3
    seed: int = 0


class GeometryConfig(BaseModel):
    timeout_s: float = 120


class EmbeddingsConfig(BaseModel):
    model: str


class ApiConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    auth: Literal["none", "tokens"] = "none"


class Config(BaseModel):
    llm: LLMConfig
    embeddings: EmbeddingsConfig
    agent: AgentConfig
    geometry: GeometryConfig
    api: ApiConfig = ApiConfig()
    output_dir: Path
    data_dir: Path


def load(path: Path) -> Config:
    return Config.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def llm_for(config: Config, model: str | None) -> LLM:
    name = model or config.llm.default
    options = config.llm.models.get(name, ModelOptions())
    # each adapter has its own output default; config overrides it, since one answer must hold the whole design
    limit = {} if options.max_tokens is None else {"max_tokens": options.max_tokens}
    if options.provider == "anthropic":
        return AnthropicLLM(name, effort=options.effort, few_shot=options.few_shot, **limit)
    if options.provider == "openai":
        if options.base_url is None:
            raise ValueError(f"{name} uses provider openai, which needs base_url in config.yaml")
        return OpenAILLM(name, options.base_url, options.api_key_env, few_shot=options.few_shot, **limit)
    return OllamaLLM(name, host=config.llm.host, num_ctx=options.num_ctx, think=options.think, few_shot=options.few_shot, **limit)


def tool_path(variable: str) -> Path | None:
    value = os.environ.get(variable)
    return Path(value) if value else None
