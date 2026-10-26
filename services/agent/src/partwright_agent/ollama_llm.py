from typing import Any

from ollama import Client

from partwright_agent.llm import Message


class OllamaLLM:
    def __init__(
        self,
        model: str,
        host: str = "http://127.0.0.1:11434",
        num_ctx: int = 16384,
        think: bool | None = None,
        max_tokens: int = 6144,
        few_shot: bool = True,
    ) -> None:
        self.name = model
        self.few_shot = few_shot
        self.num_ctx = num_ctx
        self.think = think
        self.max_tokens = max_tokens
        self._client = Client(host=host)

    def chat(self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0) -> str:
        response = self._client.chat(
            model=self.name,
            messages=[_message(m) for m in messages],
            format=schema,
            options={"temperature": temperature, "seed": seed, "num_ctx": self.num_ctx, "num_predict": self.max_tokens},
            think=self.think,
        )
        return response.message.content or ""


def _message(m: Message) -> dict[str, Any]:
    out: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.images:
        out["images"] = list(m.images)
    return out
