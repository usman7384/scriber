from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)
    data_dir: Path
    auth: Literal["none", "tokens"] = "none"
    max_repairs: int = 3
    seed: int = 0
    ollama_host: str | None = None
    public_url: str = "http://127.0.0.1:8000"
    hook_attempts: int = 4
    hook_backoff_s: float = 0.5
    generation_limit: int | None = None
