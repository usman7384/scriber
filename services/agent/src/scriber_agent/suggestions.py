from pydantic import BaseModel, ConfigDict, Field

from scriber_agent.llm import LLM, Message
from scriber_geometry import Finding
from scriber_ir import Design, ParamError, answer_json, apply_params


class Suggestion(BaseModel):
    model_config = ConfigDict(frozen=True)
    target: str
    change: dict[str, float] = Field(min_length=1)
    rationale: str


class SuggestionList(BaseModel):
    suggestions: list[Suggestion]


def suggest(design: Design, findings: list[Finding], llm: LLM, seed: int = 0) -> list[Suggestion]:
    notes = "\n".join(f"- {f.severity} {f.rule_id} on {f.part}: {f.message}" for f in findings) or "- none"
    message = (
        f"Current design:\n{answer_json(design)}\n\nFindings from manufacturing checks, rules and simulation:\n{notes}\n\n"
        "Suggest up to three improvements an engineer would accept, each a change of parameter values. Answer "
        '{"suggestions": [{"target": "<parameter or feature id>", "change": {"<parameter>": <new value>}, "rationale": "<one sentence>"}]}.'
    )
    raw = llm.chat([Message(role="user", content=message)], SuggestionList.model_json_schema(), seed)
    return [s for s in SuggestionList.model_validate_json(raw).suggestions if _applies(design, s)]


def _applies(design: Design, s: Suggestion) -> bool:
    try:
        apply_params(design, s.change)
    except ParamError:
        return False
    return True
