import base64
from typing import Any, Literal, cast

import anthropic
from anthropic.types.beta import BetaImageBlockParam, BetaMessageParam, BetaOutputConfigParam, BetaTextBlockParam

from scriber_agent.llm import Message, image_mime, strict_schema

Effort = Literal["low", "medium", "high", "xhigh", "max"]
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicLLM:
    def __init__(self, model: str, max_tokens: int = 32000, effort: Effort | None = None, few_shot: bool = True) -> None:
        self.name = model
        self.few_shot = few_shot
        self.max_tokens = max_tokens
        self.effort = effort
        self._client = anthropic.Anthropic()

    def chat(
        self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0, think: int | None = None
    ) -> str:
        # current Claude models reject sampling parameters, so seed and temperature are not sent
        config: BetaOutputConfigParam = {}
        effort = self.effort if think is None else "high" if think > 0 else "low"
        if effort:
            config["effort"] = effort
        if schema is not None:
            config["format"] = {"type": "json_schema", "schema": strict_schema(schema)}
        with self._client.beta.messages.stream(
            model=self.name,
            max_tokens=self.max_tokens,
            system="\n\n".join(m.content for m in messages if m.role == "system"),
            messages=[_turn(m) for m in messages if m.role != "system"],
            output_config=config,
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason in ("refusal", "max_tokens"):
            return ""
        return next((b.text for b in response.content if b.type == "text"), "")


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
