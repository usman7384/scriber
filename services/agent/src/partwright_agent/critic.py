from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from partwright_agent.llm import LLM, Message
from partwright_agent.prompts import CRITIC_RULES, critic_message


class Critique(BaseModel):
    model_config = ConfigDict(frozen=True)
    # findings come first so the model lists what it sees before it gives the verdict
    findings: tuple[str, ...]
    matches: bool


def critique(request: str, views: Sequence[bytes], llm: LLM, seed: int = 0) -> Critique:
    messages = [Message(role="system", content=CRITIC_RULES), Message(role="user", content=critic_message(request), images=tuple(views))]
    return Critique.model_validate_json(llm.chat(messages, Critique.model_json_schema(), seed))
