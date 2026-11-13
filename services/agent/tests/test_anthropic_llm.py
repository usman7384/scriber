from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest

from scriber_agent import AnthropicLLM, Message
from scriber_agent.llm import UNSUPPORTED, strict_schema
from scriber_agent.loop import RefineAnswer
from scriber_agent.requirements import RequirementList
from scriber_ir import json_schema


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
    assert call["system"] == [{"type": "text", "text": "rules", "cache_control": {"type": "ephemeral"}}]
    assert [m["role"] for m in call["messages"]] == ["user", "user"]
    assert call["output_config"]["effort"] == "high"
    assert call["output_config"]["format"]["schema"]["additionalProperties"] is False
    assert "temperature" not in call and "seed" not in call


def test_refused_or_cut_off_answers_come_back_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    for stop in ("refusal", "max_tokens"):
        llm, _ = _llm(monkeypatch, stop)
        assert llm.chat([Message(role="user", content="plate")], None) == ""


def test_images_go_first_as_base64_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, client = _llm(monkeypatch)
    llm.chat([Message(role="user", content="read the drawing", images=(b"\x89PNG\r\n\x1a\n",))], None)
    image, text = client.calls[0]["messages"][0]["content"]
    assert image["type"] == "image" and image["source"]["media_type"] == "image/png"
    assert text == {"type": "text", "text": "read the drawing"}


def test_a_schema_too_large_to_enforce_is_sent_as_instructions(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, client = _llm(monkeypatch)
    client.reply.content = [SimpleNamespace(type="text", text='```json\n{"a": 1}\n```')]
    stream = client.stream
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

    @contextmanager
    def refusing(**kwargs: Any) -> Iterator[SimpleNamespace]:
        if "format" in kwargs["output_config"]:
            client.calls.append(kwargs)
            raise anthropic.BadRequestError("The compiled grammar is too large", response=httpx2.Response(400, request=request), body=None)
        with stream(**kwargs) as s:
            yield s

    client.beta.messages.stream = refusing
    schema = {"title": "Design", "type": "object", "properties": {}}
    messages = [Message(role="system", content="rules"), Message(role="user", content="plate")]
    assert llm.chat(messages, schema) == '{"a": 1}'
    assert llm.chat(messages, schema) == '{"a": 1}'
    assert [("format" in c["output_config"]) for c in client.calls] == [True, False, False]
    system = client.calls[-1]["system"][0]["text"]
    assert '"title": "Design"' in system and system.startswith("rules")
    client.reply.content = [SimpleNamespace(type="text", text='The chamfer now takes only the lug holes.\n\n```json\n{"a": 2}\n```\n')]
    assert llm.chat(messages, schema) == '{"a": 2}'
    client.reply.content = [SimpleNamespace(type="text", text='Here it is: {"a": {"b": 3}} done')]
    assert llm.chat(messages, schema) == '{"a": {"b": 3}}'


def test_a_dropped_stream_is_sent_again(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, client = _llm(monkeypatch)
    stream = client.stream
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    drops = [anthropic.APIConnectionError(request=request), httpx2.RemoteProtocolError("peer closed connection")]

    @contextmanager
    def flaky(**kwargs: Any) -> Iterator[SimpleNamespace]:
        if drops:
            raise drops.pop()
        with stream(**kwargs) as s:
            yield s

    client.beta.messages.stream = flaky
    assert llm.chat([Message(role="user", content="plate")], None) == '{"a": 1}'
