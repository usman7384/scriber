from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: str
    content: str
    images: tuple[bytes, ...] = ()


Thinking = Literal["low", "high"]
THINKING_BUDGET: dict[Thinking, int] = {"low": 0, "high": 8192}
# JSON Schema keywords hosted structured-output APIs reject
UNSUPPORTED = frozenset(("discriminator", "minItems", "maxItems", "minLength", "maxLength", "pattern", "minimum", "maximum", "default"))


class LLM(Protocol):
    name: str
    few_shot: bool

    # think: reasoning-token budget; None keeps the model's own setting
    def chat(
        self, messages: list[Message], schema: dict[str, Any] | None, seed: int = 0, temperature: float = 0.0, think: int | None = None
    ) -> str: ...


def image_mime(image: bytes) -> str:
    if image.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if image[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


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
