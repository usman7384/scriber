import json
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ValidationError

from partwright_agent.grounding import grounded, measurable, misquoted
from partwright_agent.llm import LLM, THINKING_BUDGET, Message, Thinking
from partwright_agent.project_context import Grounding, cite, context_block, fact_requirements, overridden
from partwright_agent.prompts import design_messages, refine_message, repair_message, requirement_messages, resample_message
from partwright_agent.requirements import CheckResult, Requirement, RequirementList, check
from partwright_agent.standards import reference_data
from partwright_context import Fact
from partwright_geometry import Artifact, BuildError, Finding
from partwright_ir import (
    Design,
    ParamError,
    Process,
    Provenance,
    RuleSet,
    answer_json,
    apply_params,
    drop_unused_params,
    json_schema,
    normalize,
    validate,
)

REPAIR_TEMPERATURE = 0.5
STUCK_TEMPERATURE = 0.9
StepKind = Literal["requirements", "emit", "validate", "build", "check", "repair", "done", "failed"]
Build = Callable[[Design, Path], Artifact]


class Geometry(Protocol):
    def build(self, design: Design, out_dir: Path, rules: RuleSet = ..., process: Process = "any") -> Artifact: ...


class Result(BaseModel):
    design: Design | None
    artifact: Artifact | None
    checks: list[CheckResult]
    attempts: int
    repairs: int
    used: list[str] = []

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


def generate(
    prompt: str,
    llm: LLM,
    geometry: Geometry,
    out_dir: Path,
    max_repairs: int = 3,
    seed: int = 0,
    context: Grounding | None = None,
    images: tuple[bytes, ...] = (),
    thinking: Thinking | None = None,
) -> Iterator[Step]:
    clock = _Clock()
    stated = extract_requirements(prompt, llm, seed)
    facts = context.pack.facts if context else []
    dropped = overridden(stated, facts)
    reqs = stated + fact_requirements([f for f in facts if f not in dropped])
    yield _requirements_step(reqs, clock, dropped)
    project = context_block(context, dropped) if context else ""
    messages = [Message(role=r, content=c) for r, c in design_messages(prompt, reference_data(prompt), project, llm.few_shot)]
    messages[-1] = messages[-1].model_copy(update={"images": images})

    def decode(raw: str) -> Design:
        design = Design.model_validate_json(raw)
        return cite(design, context.pack) if context else design

    run = replace(_run(llm, geometry, context, out_dir, max_repairs, seed, clock), thinking=thinking)
    yield from _attempts(run, messages, json_schema(), decode, reqs, prompt)


def refine(
    design: Design,
    instruction: str,
    llm: LLM,
    geometry: Geometry,
    out_dir: Path,
    max_repairs: int = 3,
    seed: int = 0,
    context: Grounding | None = None,
    images: tuple[bytes, ...] = (),
) -> Iterator[Step]:
    clock = _Clock()
    reqs = extract_requirements(instruction, llm, seed)
    yield _requirements_step(reqs, clock)

    def decode(raw: str) -> Design:
        answer = RefineAnswer.model_validate_json(raw)
        return answer.design or apply_params(
            design, {u.name: u.value for u in answer.updates}, Provenance(source="prompt", quote=instruction)
        )

    messages = [Message(role="user", content=refine_message(answer_json(design), instruction), images=images)]
    run = _run(llm, geometry, context, out_dir, max_repairs, seed, clock)
    yield from _attempts(run, messages, RefineAnswer.model_json_schema(), decode, reqs)


def extract_requirements(text: str, llm: LLM, seed: int = 0) -> list[Requirement]:
    messages = [Message(role=r, content=c) for r, c in requirement_messages(text)]
    raw = llm.chat(messages, RequirementList.model_json_schema(), seed)
    try:
        reqs = RequirementList.model_validate_json(raw).requirements
    except ValidationError:
        return []
    return measurable(grounded(reqs, text), text)


@dataclass(frozen=True)
class _Run:
    llm: LLM
    build: Build
    out_dir: Path
    max_repairs: int
    seed: int
    clock: "_Clock"
    used: list[str]
    thinking: Thinking | None = None


def _run(llm: LLM, geometry: Geometry, context: Grounding | None, out_dir: Path, max_repairs: int, seed: int, clock: "_Clock") -> _Run:
    if context is None:
        return _Run(llm, geometry.build, out_dir, max_repairs, seed, clock, [])
    rules, process = context.rules.for_process(context.process), context.process

    def build(design: Design, attempt_dir: Path) -> Artifact:
        return geometry.build(design, attempt_dir, rules, process)

    return _Run(llm, build, out_dir, max_repairs, seed, clock, context.used_ids())


def _attempts(
    run: _Run,
    messages: list[Message],
    schema: dict[str, Any],
    decode: Callable[[str], Design],
    reqs: list[Requirement],
    request: str = "",
) -> Iterator[Step]:
    last: Result | None = None
    seen: set[str] = set()
    prompt = fresh = messages
    budget = THINKING_BUDGET[run.thinking] if run.thinking else None
    thought = f", thinking {run.thinking} with a {budget} token reasoning budget" if run.thinking else ""
    for attempt in range(1, run.max_repairs + 2):
        seed = run.seed + attempt - 1
        raw = run.llm.chat(prompt, schema, seed, 0.0 if attempt == 1 else REPAIR_TEMPERATURE, budget)
        resampled = raw in seen
        if resampled:
            # a sharply tuned model copies the quoted answer back, so ask again without quoting it
            raw = run.llm.chat(fresh, schema, seed, STUCK_TEMPERATURE, budget)
        seen.add(raw)
        note = thought + (", re-sampled because it repeated an earlier answer" if resampled else "")
        yield Step(
            kind="emit" if attempt == 1 else "repair", message=f"answer of {len(raw)} chars{note}", attempt=attempt, elapsed_ms=run.clock()
        )
        attempt_dir = run.out_dir / f"attempt_{attempt}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "answer.json").write_text(raw, encoding="utf-8")
        problems, design, artifact, checks = evaluate(raw, decode, reqs, run.build, attempt_dir, request)
        last = Result(design=design, artifact=artifact, checks=checks, attempts=attempt, repairs=attempt - 1, used=run.used)
        if not problems:
            yield Step(kind="done", message=_summary(last), attempt=attempt, elapsed_ms=run.clock(), result=last)
            return
        yield Step(kind="check", message="; ".join(problems), attempt=attempt, elapsed_ms=run.clock())
        prompt = [*messages, Message(role="user", content=repair_message(raw, problems))]
        fresh = [*messages, Message(role="user", content=resample_message(problems))]
    assert last is not None
    yield Step(kind="failed", message=f"gave up after {last.attempts} attempts", attempt=last.attempts, elapsed_ms=run.clock(), result=last)


def evaluate(
    raw: str, decode: Callable[[str], Design], reqs: list[Requirement], build: Build, out_dir: Path, request: str = ""
) -> tuple[list[str], Design | None, Artifact | None, list[CheckResult]]:
    try:
        design = drop_unused_params(normalize(decode(raw)))
    except ValidationError as e:
        return [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:8]], None, None, []
    except ParamError as e:
        return [str(e)], None, None, []
    errors = validate(design)
    if errors:
        return [str(e) for e in errors[:8]], design, None, []
    try:
        artifact = build(design, out_dir)
    except BuildError as e:
        where = f" in feature {e.feature!r}" if e.feature else ""
        hint = " The operation is impossible with the given sketch or dimensions; rethink that feature." if e.kind == "kernel" else ""
        return [f"CAD kernel error ({e.kind}){where}: {_short(e)}.{hint}"], design, None, []
    checks = check(reqs, artifact)
    problems = misquoted(design, request) if request else []
    problems += [_finding_text(f) for f in artifact.findings if f.severity == "error"]
    problems += [f"requirement not met: {c.requirement.description} (actual: {c.actual})" for c in checks if not c.passed]
    return list(dict.fromkeys(problems)), design, artifact, checks


def _finding_text(f: Finding) -> str:
    fix = f" Fix: {f.suggestion}." if f.suggestion else ""
    return f"{f.rule_id} {f.part}: {f.message}.{fix}"


def _requirements_step(reqs: list[Requirement], clock: "_Clock", dropped: Sequence[Fact] = ()) -> Step:
    message = "; ".join(r.description for r in reqs) or "none found"
    if dropped:
        message += "; the request overrides the project documents on: " + "; ".join(f"{f.text} [{f.id}]" for f in dropped)
    return Step(kind="requirements", message=message, attempt=0, elapsed_ms=clock())


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
