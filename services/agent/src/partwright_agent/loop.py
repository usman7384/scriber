import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ValidationError

from partwright_agent.grounding import grounded
from partwright_agent.llm import LLM, Message
from partwright_agent.prompts import design_messages, refine_message, repair_message, requirement_messages
from partwright_agent.requirements import CheckResult, Requirement, RequirementList, check
from partwright_geometry import Artifact, BuildError
from partwright_ir import Design, ParamError, Provenance, apply_params, json_schema, validate

REPAIR_TEMPERATURE = 0.5
StepKind = Literal["requirements", "emit", "validate", "build", "check", "repair", "done", "failed"]


class Geometry(Protocol):
    def build(self, design: Design, out_dir: Path) -> Artifact: ...


class Result(BaseModel):
    design: Design | None
    artifact: Artifact | None
    checks: list[CheckResult]
    attempts: int
    repairs: int

    @property
    def ok(self) -> bool:
        return self.artifact is not None and self.artifact.ok and all(c.passed for c in self.checks)


class Step(BaseModel):
    kind: StepKind
    message: str
    attempt: int
    elapsed_ms: int
    result: Result | None = None


class ParamUpdate(BaseModel):
    name: str
    value: float


class RefineAnswer(BaseModel):
    updates: list[ParamUpdate]
    design: Design | None


def generate(prompt: str, llm: LLM, geometry: Geometry, out_dir: Path, max_repairs: int = 3, seed: int = 0) -> Iterator[Step]:
    clock = _Clock()
    reqs = extract_requirements(prompt, llm, seed)
    yield _requirements_step(reqs, clock)
    messages = [Message(role=r, content=c) for r, c in design_messages(prompt)]
    yield from _attempts(messages, json_schema(), Design.model_validate_json, reqs, llm, geometry, out_dir, max_repairs, seed, clock)


def refine(
    design: Design, instruction: str, llm: LLM, geometry: Geometry, out_dir: Path, max_repairs: int = 3, seed: int = 0
) -> Iterator[Step]:
    clock = _Clock()
    reqs = extract_requirements(instruction, llm, seed)
    yield _requirements_step(reqs, clock)

    def decode(raw: str) -> Design:
        answer = RefineAnswer.model_validate_json(raw)
        return answer.design or apply_params(
            design, {u.name: u.value for u in answer.updates}, Provenance(source="prompt", quote=instruction)
        )

    messages = [Message(role="user", content=refine_message(design.model_dump_json(), instruction))]
    yield from _attempts(messages, RefineAnswer.model_json_schema(), decode, reqs, llm, geometry, out_dir, max_repairs, seed, clock)


def extract_requirements(text: str, llm: LLM, seed: int = 0) -> list[Requirement]:
    messages = [Message(role=r, content=c) for r, c in requirement_messages(text)]
    raw = llm.chat(messages, RequirementList.model_json_schema(), seed)
    try:
        reqs = RequirementList.model_validate_json(raw).requirements
    except ValidationError:
        return []
    return grounded(reqs, text)


def _attempts(
    messages: list[Message],
    schema: dict[str, Any],
    decode: Callable[[str], Design],
    reqs: list[Requirement],
    llm: LLM,
    geometry: Geometry,
    out_dir: Path,
    max_repairs: int,
    seed: int,
    clock: "_Clock",
) -> Iterator[Step]:
    last: Result | None = None
    previous = ""
    for attempt in range(1, max_repairs + 2):
        raw = llm.chat(messages, schema, seed + attempt - 1, 0.0 if attempt == 1 else REPAIR_TEMPERATURE)
        messages = [*messages, Message(role="assistant", content=raw)]
        yield Step(kind="emit" if attempt == 1 else "repair", message=f"answer of {len(raw)} chars", attempt=attempt, elapsed_ms=clock())
        attempt_dir = out_dir / f"attempt_{attempt}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "answer.json").write_text(raw, encoding="utf-8")
        problems, design, artifact, checks = _evaluate(raw, decode, reqs, geometry, attempt_dir)
        last = Result(design=design, artifact=artifact, checks=checks, attempts=attempt, repairs=attempt - 1)
        if not problems:
            yield Step(kind="done", message=_summary(last), attempt=attempt, elapsed_ms=clock(), result=last)
            return
        yield Step(kind="check", message="; ".join(problems), attempt=attempt, elapsed_ms=clock())
        messages = [*messages, Message(role="user", content=repair_message(problems, unchanged=raw == previous))]
        previous = raw
    assert last is not None
    yield Step(kind="failed", message=f"gave up after {last.attempts} attempts", attempt=last.attempts, elapsed_ms=clock(), result=last)


def _evaluate(
    raw: str, decode: Callable[[str], Design], reqs: list[Requirement], geometry: Geometry, out_dir: Path
) -> tuple[list[str], Design | None, Artifact | None, list[CheckResult]]:
    try:
        design = decode(raw)
    except ValidationError as e:
        return [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:8]], None, None, []
    except ParamError as e:
        return [str(e)], None, None, []
    errors = validate(design)
    if errors:
        return [str(e) for e in errors[:8]], design, None, []
    try:
        artifact = geometry.build(design, out_dir)
    except BuildError as e:
        where = f" in feature {e.feature!r}" if e.feature else ""
        hint = " The operation is impossible with the given sketch or dimensions; rethink that feature." if e.kind == "kernel" else ""
        return [f"CAD kernel error ({e.kind}){where}: {_short(e)}.{hint}"], design, None, []
    checks = check(reqs, artifact)
    problems = [f"{f.rule_id} {f.part}: {f.message}" for f in artifact.findings if f.severity == "error"]
    problems += [f"requirement not met: {c.requirement.description} (actual: {c.actual})" for c in checks if not c.passed]
    return problems, design, artifact, checks


def _requirements_step(reqs: list[Requirement], clock: "_Clock") -> Step:
    return Step(kind="requirements", message="; ".join(r.description for r in reqs) or "none found", attempt=0, elapsed_ms=clock())


def _summary(r: Result) -> str:
    passed = sum(c.passed for c in r.checks)
    return f"{r.design.title if r.design else '?'}: {passed}/{len(r.checks)} requirement checks passed, {r.repairs} repairs"


def _short(e: Exception, limit: int = 600) -> str:
    text = str(e)
    return text if len(text) <= limit else text[:limit] + " ..."


class _Clock:
    def __init__(self) -> None:
        self.start = time.monotonic()

    def __call__(self) -> int:
        return int((time.monotonic() - self.start) * 1000)


def dump_steps(steps: list[Step]) -> str:
    return json.dumps([s.model_dump(mode="json", exclude={"result"}) for s in steps], indent=2)
