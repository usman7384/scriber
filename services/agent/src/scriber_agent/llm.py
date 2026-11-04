from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: str
    content: str
    images: tuple[bytes, ...] = ()


Thinking = Literal["low", "high"]
THINKING_BUDGET: dict[Thinking, int] = {"low": 0, "high": 8192}


class LLM(Protocol):
    name: str
    few_shot: bool

    # think: reasoning-token budget; None keeps the model's own setting
    def chat(
        self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0, think: int | None = None
    ) -> str: ...
