from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: str
    content: str
    images: tuple[bytes, ...] = ()


class LLM(Protocol):
    name: str

    def chat(self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0) -> str: ...
