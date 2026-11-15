from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from scriber_agent.llm import LLM, Message
from scriber_agent.prompts import CRITIC_RULES, OUTLINE_RULES, critic_message, outline_message


class Critique(BaseModel):
    model_config = ConfigDict(frozen=True)
    # findings come first so the model lists what it sees before it gives the verdict
    findings: tuple[str, ...]
    matches: bool


def critique(request: str, views: Sequence[bytes], llm: LLM, seed: int = 0, reference: Sequence[bytes] = ()) -> Critique:
    content = critic_message(request, len(reference))
    messages = [Message(role="system", content=CRITIC_RULES), Message(role="user", content=content, images=(*reference, *views))]
    return Critique.model_validate_json(llm.chat(messages, Critique.model_json_schema(), seed))


def outline_critique(
    request: str, views: Sequence[bytes], llm: LLM, size: tuple[float, float, float], seed: int = 0, reference: Sequence[bytes] = ()
) -> Critique:
    content = outline_message(request, len(reference), size)
    messages = [Message(role="system", content=OUTLINE_RULES), Message(role="user", content=content, images=(*reference, *views))]
    return Critique.model_validate_json(llm.chat(messages, Critique.model_json_schema(), seed))
