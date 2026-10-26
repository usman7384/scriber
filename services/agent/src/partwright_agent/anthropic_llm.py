from typing import Any, Literal

import anthropic
from anthropic.types.beta import BetaMessageParam, BetaOutputConfigParam

from partwright_agent.llm import Message

Effort = Literal["low", "medium", "high", "xhigh", "max"]
FALLBACK_BETA = "server-side-fallback-2026-07-01"
UNSUPPORTED = frozenset(("discriminator", "minItems", "maxItems", "minLength", "maxLength", "pattern", "minimum", "maximum", "default"))


class AnthropicLLM:
    def __init__(self, model: str, max_tokens: int = 32000, effort: Effort | None = None, few_shot: bool = True) -> None:
        self.name = model
        self.few_shot = few_shot
        self.max_tokens = max_tokens
        self.effort = effort
        self._client = anthropic.Anthropic()

    def chat(self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0) -> str:
        # current Claude models reject sampling parameters, so seed and temperature are not sent
        config: BetaOutputConfigParam = {}
        if self.effort:
            config["effort"] = self.effort
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
    return {"role": "user", "content": m.content}


def strict_schema(node: Any) -> Any:
    if isinstance(node, list):
        return [strict_schema(n) for n in node]
    if not isinstance(node, dict):
        return node
    out = {("anyOf" if k == "oneOf" else k): strict_schema(v) for k, v in node.items() if k not in UNSUPPORTED and k != "prefixItems"}
    if "prefixItems" in node:
        out["items"] = {"anyOf": strict_schema(node["prefixItems"])}
    if out.get("type") == "object" and "properties" in out:
        out["additionalProperties"] = False
    return out
