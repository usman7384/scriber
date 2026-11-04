from pydantic import BaseModel, ConfigDict, Field

from scriber_agent.llm import LLM, Message
from scriber_ir import Design, answer_json


class VariantPlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    param: str
    values: list[float] = Field(min_length=1, max_length=1000)


def plan_variants(design: Design, instruction: str, llm: LLM, seed: int = 0) -> VariantPlan:
    message = (
        f"Current design:\n{answer_json(design)}\n\nVariant request: {instruction}\n\n"
        'Which one parameter do the variants change, and to which values? Answer {"param": "<parameter name>", "values": [...]}, '
        "one value per variant, in the order the request gives them."
    )
    raw = llm.chat([Message(role="user", content=message)], VariantPlan.model_json_schema(), seed)
    plan = VariantPlan.model_validate_json(raw)
    if plan.param not in design.param_values():
        raise ValueError(f"variant parameter {plan.param!r} is not one of {sorted(design.param_values())}")
    return plan
