import json
from typing import Any

import httpx
import pytest

from scriber_agent import Message, OpenAILLM

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 8


def _llm(monkeypatch: pytest.MonkeyPatch, *replies: httpx.Response) -> tuple[OpenAILLM, list[httpx.Request]]:
    monkeypatch.setenv("TEST_KEY", "k")
    llm = OpenAILLM("some-model", "https://api.example.test/v1/", api_key_env="TEST_KEY")
    seen: list[httpx.Request] = []
    queue = list(replies)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0)

    llm._client = httpx.Client(headers=llm._client.headers, transport=httpx.MockTransport(handler))
    return llm, seen


def _answer(content: str, finish: str = "stop") -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"finish_reason": finish, "message": {"content": content}}]})


def _body(request: httpx.Request) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(request.content)
    return body


def test_request_carries_schema_sampling_and_key(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, seen = _llm(monkeypatch, _answer('{"a": 1}'), _answer("{}"))
    messages = [Message(role="system", content="rules"), Message(role="user", content="plate")]
    schema_in = {"type": "object", "properties": {"a": {"type": "integer", "minimum": 0}}}
    assert llm.chat(messages, schema_in, seed=3, temperature=0.5) == '{"a": 1}'
    request = seen[0]
    body = _body(request)
    assert str(request.url) == "https://api.example.test/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer k"
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert body["temperature"] == 0.5 and "seed" not in body
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["additionalProperties"] is False and "minimum" not in schema["properties"]["a"]
    assert "reasoning_effort" not in body
    llm.chat(messages, None, think=8192)
    assert _body(seen[1])["reasoning_effort"] == "high" and "response_format" not in _body(seen[1])


def test_images_go_as_data_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, seen = _llm(monkeypatch, _answer("ok"))
    llm.chat([Message(role="user", content="read this", images=(PNG,))], None)
    text, image = _body(seen[0])["messages"][0]["content"]
    assert text == {"type": "text", "text": "read this"}
    assert image["image_url"]["url"].startswith("data:image/png;base64,")


def test_cut_off_answer_comes_back_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, _ = _llm(monkeypatch, _answer('{"a": ', finish="length"))
    assert llm.chat([Message(role="user", content="plate")], None) == ""


def test_rate_limits_and_overload_wait_then_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []
    monkeypatch.setattr("scriber_agent.openai_llm.time.sleep", waits.append)
    llm, seen = _llm(monkeypatch, httpx.Response(429, headers={"retry-after": "7"}), httpx.Response(503), _answer("{}"))
    assert llm.chat([Message(role="user", content="plate")], None) == "{}"
    assert waits == [7.0, 30.0] and len(seen) == 3


def test_errors_name_the_model_and_the_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    llm, _ = _llm(monkeypatch, httpx.Response(400, text="schema keyword not supported"))
    with pytest.raises(RuntimeError, match=r"some-model: HTTP 400 .*schema keyword not supported"):
        llm.chat([Message(role="user", content="plate")], None)


def test_missing_key_fails_before_any_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_SUCH_KEY", raising=False)
    with pytest.raises(ValueError, match="NO_SUCH_KEY"):
        OpenAILLM("some-model", "https://api.example.test/v1", api_key_env="NO_SUCH_KEY")


def test_local_servers_need_no_key() -> None:
    assert "authorization" not in OpenAILLM("local", "http://127.0.0.1:1234/v1")._client.headers


def test_no_output_limit_is_sent_unless_set_and_tokens_are_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    usage = {"prompt_tokens": 500, "completion_tokens": 900, "completion_tokens_details": {"reasoning_tokens": 400}}
    reply = httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}], "usage": usage})
    llm, seen = _llm(monkeypatch, reply, _answer("{}"))
    llm.chat([Message(role="user", content="plate")], None)
    assert "max_tokens" not in _body(seen[0]) and llm.usage.output == 900 and llm.usage.thinking == 400
    llm.max_tokens = 2000
    llm.chat([Message(role="user", content="plate")], None)
    assert _body(seen[1])["max_tokens"] == 2000
