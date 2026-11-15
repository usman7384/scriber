import base64
import os
import time
from typing import Any

import httpx

from scriber_agent.llm import Message, Usage, image_mime, strict_schema

RETRIES = 4
TRANSIENT = frozenset((429, 500, 502, 503, 504))


class OpenAILLM:
    def __init__(
        self,
        model: str,
        base_url: str,
        api_key_env: str | None = None,
        max_tokens: int | None = None,
        few_shot: bool = True,
        timeout_s: float = 600,
    ) -> None:
        self.name = model
        self.few_shot = few_shot
        # None leaves the field out, so the server allows the model's own output limit
        self.max_tokens = max_tokens
        self.usage = Usage()
        self.url = base_url.rstrip("/") + "/chat/completions"
        headers = {}
        if api_key_env:
            key = os.environ.get(api_key_env)
            if not key:
                raise ValueError(f"{model} needs an API key in the {api_key_env} environment variable")
            headers["Authorization"] = f"Bearer {key}"
        self._client = httpx.Client(headers=headers, timeout=timeout_s)

    def chat(
        self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0, think: int | None = None
    ) -> str:
        # no seed: Gemini rejects the field, and hosted models are not reproducible anyway
        body: dict[str, Any] = {
            "model": self.name,
            "messages": [_message(m) for m in messages],
            "temperature": temperature,
        }
        if self.max_tokens is not None:
            body["max_tokens"] = self.max_tokens
        if schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": strict_schema(schema)}}
        if think is not None:
            body["reasoning_effort"] = "high" if think > 0 else "low"
        reply = self._post(body)
        self._count(reply.get("usage") or {})
        choice = reply["choices"][0]
        if choice.get("finish_reason") == "length":
            return ""
        return str(choice["message"].get("content") or "")

    def _count(self, used: dict[str, Any]) -> None:
        thinking = (used.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
        cached = (used.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        self.usage += Usage(used.get("prompt_tokens") or 0, used.get("completion_tokens") or 0, thinking, cached)

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(RETRIES + 1):
            response = self._client.post(self.url, json=body)
            if response.status_code not in TRANSIENT or attempt == RETRIES:
                break
            # rate limits and overloaded servers pass; wait as told, else back off
            time.sleep(_wait(response.headers.get("retry-after"), attempt))
        if response.is_error:
            raise RuntimeError(f"{self.name}: HTTP {response.status_code} from {self.url}: {response.text[:500]}")
        result: dict[str, Any] = response.json()
        return result


def _wait(retry_after: str | None, attempt: int) -> float:
    try:
        return float(retry_after or "")
    except ValueError:
        return 15.0 * 2.0**attempt


def _message(m: Message) -> dict[str, Any]:
    if not m.images:
        return {"role": m.role, "content": m.content}
    parts: list[dict[str, Any]] = [{"type": "text", "text": m.content}]
    parts += [{"type": "image_url", "image_url": {"url": f"data:{image_mime(i)};base64,{base64.b64encode(i).decode()}"}} for i in m.images]
    return {"role": m.role, "content": parts}
