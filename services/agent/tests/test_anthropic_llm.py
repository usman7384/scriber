from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from partwright_agent import AnthropicLLM, Message
from partwright_agent.anthropic_llm import UNSUPPORTED, strict_schema
from partwright_agent.loop import RefineAnswer
from partwright_agent.requirements import RequirementList
from partwright_ir import json_schema


def _nodes(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _nodes(v)
    elif isinstance(node, list):
        for v in node:
            yield from _nodes(v)


@pytest.mark.parametrize("schema", [json_schema(), RequirementList.model_json_schema(), RefineAnswer.model_json_schema()])
def test_schemas_use_only_what_structured_outputs_accept(schema: dict[str, Any]) -> None:
    nodes = list(_nodes(strict_schema(schema)))
    assert not any(k in n for n in nodes for k in (*UNSUPPORTED, "oneOf", "prefixItems"))
    assert all(n.get("additionalProperties") is False for n in nodes if n.get("type") == "object" and "properties" in n)


class FakeClient:
    def __init__(self, reply: SimpleNamespace) -> None:
        self.calls: list[dict[str, Any]] = []
        self.reply = reply
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self.stream))

    @contextmanager
    def stream(self, **kwargs: Any) -> Iterator[SimpleNamespace]:
        self.calls.append(kwargs)
        yield SimpleNamespace(get_final_message=lambda: self.reply)


def _llm(monkeypatch: pytest.MonkeyPatch, stop: str = "end_turn") -> tuple[AnthropicLLM, FakeClient]:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    llm = AnthropicLLM("claude-sonnet-5-5", effort="high")
    reply = SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text='{"a": 1}')])
    client = FakeClient(reply)
    monkeypatch.setattr(llm, "_client", client)
    return llm, client


def test_request_moves_system_text_out_and_sends_no_sampling(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, client = _llm(monkeypatch)
    messages = [Message(role="system", content="rules"), Message(role="user", content="plate"), Message(role="user", content="fix it")]
    assert llm.chat(messages, {"type": "object", "properties": {}}, seed=3, temperature=0.9) == '{"a": 1}'
    call = client.calls[0]
    assert call["system"] == "rules"
    assert [m["role"] for m in call["messages"]] == ["user", "user"]
    assert call["output_config"]["effort"] == "high"
    assert call["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert "temperature" not in call and "seed" not in call


def test_refused_or_cut_off_answers_come_back_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    for stop in ("refusal", "max_tokens"):
        llm, _ = _llm(monkeypatch, stop)
        assert llm.chat([Message(role="user", content="plate")], None) == ""
