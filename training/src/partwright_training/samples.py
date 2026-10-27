import json
import random
import re
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from partwright_agent import (
    Grounding,
    Requirement,
    context_block,
    design_messages,
    evaluate,
    reference_data,
    repair_message,
    requirement_messages,
)
from partwright_geometry import LocalGeometry
from partwright_ir import Design, answer_json
from partwright_training.context import RULES
from partwright_training.mutate import mutate
from partwright_training.render import Prompt
from partwright_training.spec import Spec, num

STATED_KINDS = ("extent", "holes", "hole_spacing", "wall")


@dataclass(frozen=True)
class Sample:
    kind: str
    family: str
    style: str
    detail: str
    messages: tuple[tuple[str, str], ...]

    def record(self) -> dict[str, Any]:
        messages = [{"role": r, "content": c} for r, c in self.messages]
        return {"kind": self.kind, "family": self.family, "style": self.style, "detail": self.detail, "messages": messages}


def target(spec: Spec) -> str:
    return answer_json(spec.design)


@dataclass(frozen=True)
class Task:
    prompt: Prompt
    context: Grounding | None
    design: Design

    def messages(self) -> tuple[tuple[str, str], ...]:
        project = context_block(self.context) if self.context else ""
        return tuple(design_messages(self.prompt.text, reference_data(self.prompt.text), project, few_shot=False))

    def answer(self) -> str:
        return answer_json(self.design)

    def detail(self) -> str:
        return "" if self.context is None else "context+facts" if self.context.pack.facts else "context"


def generate_sample(spec: Spec, task: Task) -> Sample:
    return Sample("generate", spec.family, task.prompt.style, task.detail(), (*task.messages(), ("assistant", task.answer())))


def repair_sample(spec: Spec, task: Task, geometry: LocalGeometry, out_dir: Path, rng: random.Random, tries: int = 4) -> Sample | None:
    good = json.loads(task.answer())
    for attempt in range(tries):
        mutated = mutate(good, rng)
        if mutated is None:
            return None
        name, raw = mutated
        build = partial(geometry.build, rules=RULES)
        problems, _, _, _ = evaluate(raw, Design.model_validate_json, list(spec.checks), build, out_dir / f"repair_{attempt}")
        if problems:
            repair = repair_message(raw, problems)
            messages = (*task.messages(), ("user", repair), ("assistant", task.answer()))
            return Sample("repair", spec.family, task.prompt.style, name, messages)
    return None


def requirement_sample(spec: Spec, prompt: Prompt) -> Sample | None:
    stated = [r for r in spec.checks if r.kind in STATED_KINDS and _stated(r, prompt.text)]
    if not stated and prompt.style not in ("vague", "documented"):
        return None
    answer = {"requirements": [r.model_dump(mode="json", exclude_defaults=True) for r in stated]}
    messages = (*requirement_messages(prompt.text), ("assistant", json.dumps(answer, separators=(",", ":"))))
    return Sample("requirements", spec.family, prompt.style, "", messages)


def _stated(r: Requirement, text: str) -> bool:
    if "tap" in r.description:
        return False
    return r.value is None or re.search(rf"(?<![\d.]){re.escape(num(r.value))}(?![\d.])", text) is not None
