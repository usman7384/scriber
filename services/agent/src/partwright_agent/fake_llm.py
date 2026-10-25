from typing import Any

from partwright_agent.llm import Message


class FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.name = "fake"
        self.responses = list(responses)
        self.calls: list[list[Message]] = []

    def chat(self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0) -> str:
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("FakeLLM ran out of scripted responses")
        return self.responses.pop(0)
