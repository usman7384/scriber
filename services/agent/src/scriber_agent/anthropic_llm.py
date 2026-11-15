import base64
import json
import re
from typing import Any, Literal, cast

import anthropic
import httpx2
from anthropic.types.beta import BetaImageBlockParam, BetaMessageParam, BetaOutputConfigParam, BetaTextBlockParam

from scriber_agent.llm import Message, Usage, image_mime, strict_schema

Effort = Literal["low", "medium", "high", "xhigh", "max"]
FALLBACK_BETA = "server-side-fallback-2026-07-01"
TOO_LARGE = "grammar is too large"
STREAM_TRIES = 3
# the limit used when the Models API cannot be asked for the model's own
FALLBACK_MAX_TOKENS = 64000
FENCED = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


class AnthropicLLM:
    def __init__(
        self, model: str, max_tokens: int | None = None, effort: Effort | None = "low", few_shot: bool = True, thinking: bool = False
    ) -> None:
        self.name = model
        self.few_shot = few_shot
        # None lets one answer use as much as the model allows: a dense design can need far more than a fixed cap
        self.max_tokens = max_tokens
        self.effort = effort
        self.thinking = thinking
        self.usage = Usage()
        self._client = anthropic.Anthropic()
        self._unenforced: set[str] = set()
        self._ceiling: int | None = None

    def chat(
        self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0, think: int | None = None
    ) -> str:
        # current Claude models reject sampling parameters, so seed and temperature are not sent
        config: BetaOutputConfigParam = {}
        if self.effort:
            config["effort"] = self.effort
        # effort sets how hard the model works; thinking is a separate switch, off unless asked for
        thinking = self.thinking if think is None else think > 0
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        if schema is None:
            return self._send(messages, system, config, thinking)
        title = str(schema.get("title", ""))
        if title not in self._unenforced:
            try:
                return self._send(
                    messages, system, {**config, "format": {"type": "json_schema", "schema": strict_schema(schema)}}, thinking
                )
            except anthropic.BadRequestError as e:
                if TOO_LARGE not in str(e):
                    raise
                # the IR schema is past what the API can enforce; describe it instead, validation and repair catch slips
                self._unenforced.add(title)
        system += "\n\nAnswer with one JSON object that follows this JSON Schema and nothing else:\n" + json.dumps(schema)
        return _unfenced(self._send(messages, system, config, thinking))

    def _send(self, messages: list[Message], system: str, config: BetaOutputConfigParam, thinking: bool) -> str:
        # the SDK retries a failed request, not a stream that drops after minutes of a long answer
        for _ in range(STREAM_TRIES - 1):
            try:
                return self._stream(messages, system, config, thinking)
            except (anthropic.APIConnectionError, httpx2.TransportError):
                continue
        return self._stream(messages, system, config, thinking)

    def _limit(self) -> int:
        if self.max_tokens is not None:
            return self.max_tokens
        if self._ceiling is None:
            try:
                self._ceiling = self._client.models.retrieve(self.name).max_tokens or FALLBACK_MAX_TOKENS
            except anthropic.APIError:
                self._ceiling = FALLBACK_MAX_TOKENS
        return self._ceiling

    def _stream(self, messages: list[Message], system: str, config: BetaOutputConfigParam, thinking: bool) -> str:
        extra: dict[str, Any] = {"thinking": {"type": "adaptive"}} if thinking else {}
        with self._client.beta.messages.stream(
            model=self.name,
            max_tokens=self._limit(),
            # the rules, examples and schema repeat on every attempt of a run, so they are cached
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[_turn(m) for m in messages if m.role != "system"],
            output_config=config,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            **extra,
        ) as stream:
            response = stream.get_final_message()
        self._count(response)
        if response.stop_reason in ("refusal", "max_tokens"):
            return ""
        return next((b.text for b in response.content if b.type == "text"), "")

    def _count(self, response: Any) -> None:
        used = getattr(response, "usage", None)
        if used is None:
            return
        details = getattr(used, "output_tokens_details", None)
        thinking = details.thinking_tokens if details else 0
        self.usage += Usage(used.input_tokens, used.output_tokens, thinking, used.cache_read_input_tokens or 0)


def _unfenced(text: str) -> str:
    # without an enforced schema the model may explain itself first; the JSON is its last fenced block, or the outer braces
    blocks = FENCED.findall(text)
    if blocks:
        return str(blocks[-1]).strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if 0 <= start < end else text.strip()


def _turn(m: Message) -> BetaMessageParam:
    if m.role == "assistant":
        return {"role": "assistant", "content": m.content}
    if not m.images:
        return {"role": "user", "content": m.content}
    blocks: list[BetaImageBlockParam | BetaTextBlockParam] = [_image(i) for i in m.images]
    return {"role": "user", "content": [*blocks, {"type": "text", "text": m.content}]}


def _image(image: bytes) -> BetaImageBlockParam:
    media = cast(Literal["image/jpeg", "image/png", "image/gif", "image/webp"], image_mime(image))
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": base64.b64encode(image).decode()}}
