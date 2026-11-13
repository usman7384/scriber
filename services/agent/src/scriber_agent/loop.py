import json
import time
from collections.abc import Callable, Generator, Iterator, Sequence
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ValidationError

from scriber_agent.critic import critique
from scriber_agent.grounding import grounded, measurable, unquote
from scriber_agent.images import TILE_NOTE, with_tiles
from scriber_agent.llm import LLM, THINKING_BUDGET, Message, Thinking
from scriber_agent.project_context import Grounding, cite, context_block, fact_requirements, overridden
from scriber_agent.prompts import (
    DRAWING_REQUIREMENTS,
    IMAGE_NOTE,
    REQUIREMENT_RULES,
    design_messages,
    refine_message,
    repair_message,
    requirement_messages,
    resample_message,
)
from scriber_agent.requirements import CheckResult, Requirement, RequirementList, check
from scriber_agent.stages import PLAN_NOTE, Changes, StagePlan, change_repair, merged, stage_message, stage_repair
from scriber_agent.standards import reference_data
from scriber_context import Fact
from scriber_geometry import Artifact, BuildError, Finding
from scriber_ir import (
    ComponentError,
    Design,
    ParamError,
    Process,
    Provenance,
    RuleSet,
    answer_json,
    apply_params,
    drop_unused_params,
    insert,
    json_schema,
    normalize,
    scope,
    splice,
    validate,
)

REPAIR_TEMPERATURE = 0.5
PLACE_NOTE = (
    "The part goes into an existing assembly at its connector {mate!r}. Add "
    '"assembly": {{"connectors": [{{"id": ..., "part": <the part id>, "origin": [x, y, z]}}]}} with one connector '
    "on the part where it seats; the part is placed so that this connector meets {mate!r}, z axes aligned."
)
STUCK_TEMPERATURE = 0.9
# a stage that still does not build after this many answers is left out; the full design's repairs can still add it
STAGE_TRIES = 2
# a design longer than this is repaired by its changes: writing it whole again can run past the output limit
LONG_DESIGN = 12_000
# a built part is compared with the input image at most this often, so a noisy critic cannot use up every repair
REVIEWS = 2
# a check that fails this many built attempts in a row is more likely misread than unmet, so it stops driving repairs
STUCK = 3
SKIPPED = "blend_skipped"
StepKind = Literal["requirements", "plan", "emit", "validate", "build", "check", "repair", "done", "failed"]
Build = Callable[[Design, Path], Artifact]


class Geometry(Protocol):
    def build(self, design: Design, out_dir: Path, rules: RuleSet = ..., process: Process = "any") -> Artifact: ...

    def thumbnail(self, glb: Path, png: Path, size: int = 256, view: str = "iso") -> Path: ...


class Result(BaseModel):
    design: Design | None
    artifact: Artifact | None
    checks: list[CheckResult]
    attempts: int
    repairs: int
    used: list[str] = []
    disputed: list[str] = []

    @property
    def ok(self) -> bool:
        checked = all(c.passed or c.requirement.description in self.disputed for c in self.checks)
        return self.artifact is not None and self.artifact.ok and checked


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
    vision: LLM | None = None,
    staged: bool = False,
) -> Iterator[Step]:
    clock = _Clock()
    stated = extract_requirements(prompt, llm, seed)
    shown = with_tiles(images)
    note = IMAGE_NOTE + (TILE_NOTE if len(shown) > len(images) else "")
    if images and vision:
        stated = stated + drawing_requirements(shown, vision, seed)
    facts = context.pack.facts if context else []
    dropped = overridden(stated, facts)
    reqs = stated + fact_requirements([f for f in facts if f not in dropped])
    yield _requirements_step(reqs, clock, dropped)
    project = context_block(context, dropped) if context else ""
    designer = vision if images and vision else llm
    messages = [Message(role=r, content=c) for r, c in design_messages(prompt, reference_data(prompt), project, designer.few_shot)]
    if images:
        messages[-1] = messages[-1].model_copy(update={"content": messages[-1].content + note, "images": shown})

    def decode(raw: str) -> Design:
        design = Design.model_validate_json(raw)
        return cite(design, context.pack) if context else design

    review = _reviewer(geometry, vision, images, prompt, seed) if images and vision else None
    run = replace(_run(designer, geometry, context, out_dir, max_repairs, seed, clock), thinking=thinking, review=review)
    first = (yield from _staged(run, messages, decode)) if staged else None
    yield from _attempts(run, messages, json_schema(), decode, reqs, prompt, first)


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
    vision: LLM | None = None,
    target: str | None = None,
) -> Iterator[Step]:
    clock = _Clock()
    reqs = extract_requirements(instruction, llm, seed)
    yield _requirements_step(reqs, clock)
    shown = design if target is None else scope(design, target)

    def decode(raw: str) -> Design:
        answer = RefineAnswer.model_validate_json(raw)
        edited = answer.design or apply_params(
            shown, {u.name: u.value for u in answer.updates}, Provenance(source="prompt", quote=instruction)
        )
        return edited if target is None else splice(design, edited, target)

    content = refine_message(answer_json(shown), instruction) + (IMAGE_NOTE if images else "")
    messages = [Message(role="user", content=content, images=images)]
    run = _run(vision if images and vision else llm, geometry, context, out_dir, max_repairs, seed, clock)
    yield from _attempts(run, messages, RefineAnswer.model_json_schema(), decode, reqs)


def place(
    prompt: str,
    target: Design,
    mate: str,
    llm: LLM,
    geometry: Geometry,
    out_dir: Path,
    max_repairs: int = 3,
    seed: int = 0,
) -> Iterator[Step]:
    clock = _Clock()
    request = f"{prompt}\n\n{PLACE_NOTE.format(mate=mate)}"
    messages = [Message(role=r, content=c) for r, c in design_messages(request, reference_data(prompt), "", llm.few_shot)]

    def decode(raw: str) -> Design:
        return insert(target, Design.model_validate_json(raw), mate)

    run = _run(llm, geometry, None, out_dir, max_repairs, seed, clock)
    # size requirements would be checked against the whole assembly; the interference and mate checks verify the placement
    yield from _attempts(run, messages, json_schema(), decode, [], prompt)


def extract_requirements(text: str, llm: LLM, seed: int = 0) -> list[Requirement]:
    messages = [Message(role=r, content=c) for r, c in requirement_messages(text)]
    raw = llm.chat(messages, RequirementList.model_json_schema(), seed)
    try:
        reqs = RequirementList.model_validate_json(raw).requirements
    except ValidationError:
        return []
    return measurable(grounded(reqs, text), text)


def drawing_requirements(images: tuple[bytes, ...], vision: LLM, seed: int = 0) -> list[Requirement]:
    messages = [Message(role="system", content=REQUIREMENT_RULES), Message(role="user", content=DRAWING_REQUIREMENTS, images=images)]
    raw = vision.chat(messages, RequirementList.model_json_schema(), seed)
    try:
        reqs = RequirementList.model_validate_json(raw).requirements
    except ValidationError:
        return []
    # drawings place holes by offsets along an axis, which a centre-to-centre spacing check misreads
    return [r for r in reqs if r.kind in ("holes", "threads")]


Review = Callable[[Artifact, Path], list[str]]


def _reviewer(geometry: Geometry, vision: LLM, reference: tuple[bytes, ...], request: str, seed: int) -> Review:
    def review(artifact: Artifact, attempt_dir: Path) -> list[str]:
        # a drawing shows straight views, so the critic gets them too, not only the iso
        glb = artifact.files["glb"]
        views = [geometry.thumbnail(glb, attempt_dir / f"review_{v}.png", 768, v).read_bytes() for v in ("iso", "top", "front")]
        try:
            verdict = critique(request, views, vision, seed, reference)
        except ValidationError:
            return []  # no verdict is not a finding
        return [] if verdict.matches else [f"compared with the attached image: {f}" for f in verdict.findings]

    return review


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
    review: Review | None = None


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
    first: str | None = None,
) -> Iterator[Step]:
    best: tuple[tuple[bool, int], Result] | None = None
    told: set[str] = set()
    seen: set[str] = set()
    reviews = 0
    reviewed: list[tuple[int, int, Result]] = []
    misses: dict[str, int] = {}
    set_aside: set[str] = set()
    prompt = fresh = messages
    base: Design | None = None
    ask = schema
    budget = THINKING_BUDGET[run.thinking] if run.thinking else None
    thought = f", thinking {run.thinking} with a {budget} token reasoning budget" if run.thinking else ""
    for attempt in range(1, run.max_repairs + 2):
        seed = run.seed + attempt - 1
        given = first if attempt == 1 else None
        raw = given or run.llm.chat(prompt, ask, seed, 0.0 if attempt == 1 else REPAIR_TEMPERATURE, budget)
        if not raw.strip():
            # the output limit ran out, usually on reasoning: ask once more without spending a repair
            again = change_repair(["the previous answer was empty"]) if base else repair_message("", [])
            raw = run.llm.chat([*prompt, Message(role="user", content=again)], ask, seed, REPAIR_TEMPERATURE, budget)
        resampled = bool(raw.strip()) and raw in seen
        if resampled:
            # a sharply tuned model copies the quoted answer back, so ask again without quoting it
            raw = run.llm.chat(fresh, ask, seed, STUCK_TEMPERATURE, budget)
        seen.add(raw)
        note = (
            thought
            + (", re-sampled because it repeated an earlier answer" if resampled else "")
            + (", built up in stages" if given else "")
        )
        yield Step(
            kind="emit" if attempt == 1 else "repair", message=f"answer of {len(raw)} chars{note}", attempt=attempt, elapsed_ms=run.clock()
        )
        attempt_dir = run.out_dir / f"attempt_{attempt}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "answer.json").write_text(raw, encoding="utf-8")
        read = decode if base is None else partial(_changed, base)
        problems, design, artifact, checks = evaluate(raw, read, reqs, run.build, attempt_dir, request)
        for c in checks:
            misses[c.requirement.description] = 0 if c.passed else misses.get(c.requirement.description, 0) + 1
        stuck = {d for d, n in misses.items() if n >= STUCK} - set_aside
        if stuck:
            set_aside |= stuck
            note = "; ".join(sorted(stuck))
            yield Step(
                kind="check",
                message=f"set aside after {STUCK} failed attempts, probably misread: {note}",
                attempt=attempt,
                elapsed_ms=run.clock(),
            )
        problems = [p for p in problems if not any(p.startswith(f"requirement not met: {d} (") for d in set_aside)]
        # a skipped blend is reported once; after that the part is accepted with that edge sharp
        problems = [p for p in problems if not (p.startswith(SKIPPED) and p in told)]
        told |= {p for p in problems if p.startswith(SKIPPED)}
        last = Result(
            design=design,
            artifact=artifact,
            checks=checks,
            attempts=attempt,
            repairs=attempt - 1,
            used=run.used,
            disputed=sorted(set_aside),
        )
        if not problems and artifact and run.review:
            findings = run.review(artifact, attempt_dir)
            reviewed.append((len(findings), attempt, last))
            if findings and reviews < REVIEWS and attempt <= run.max_repairs:
                reviews += 1
                problems = findings
        if not problems:
            # once reviews run out the newest part is still reviewed: an earlier one the critic liked better wins
            kept = min(reviewed, key=lambda r: (r[0], -r[1]))[2] if reviewed else last
            note = "" if kept is last else f"; kept attempt {kept.attempts}, which the review judged closer"
            yield Step(kind="done", message=_summary(kept) + note, attempt=attempt, elapsed_ms=run.clock(), result=kept)
            return
        rank = (artifact is not None, -len(problems))
        if best is None or rank >= best[0]:
            best = (rank, last)
        yield Step(kind="check", message="; ".join(problems), attempt=attempt, elapsed_ms=run.clock())
        # a long design is not written again: the repair answers only its changes, merged into this design
        base = design if design is not None and len(answer_json(design)) > LONG_DESIGN else None
        ask = schema if base is None else Changes.model_json_schema()
        if base is None:
            prompt = [*messages, Message(role="user", content=repair_message(raw, problems))]
            fresh = [*messages, Message(role="user", content=resample_message(problems))]
        else:
            prompt = fresh = [
                *messages,
                Message(role="assistant", content=answer_json(base)),
                Message(role="user", content=change_repair(problems)),
            ]
    assert best is not None
    kept = best[1]
    message = f"gave up after {run.max_repairs + 1} attempts; kept attempt {kept.attempts}, the best one"
    yield Step(kind="failed", message=message, attempt=run.max_repairs + 1, elapsed_ms=run.clock(), result=kept)


def _changed(base: Design, raw: str) -> Design:
    return merged(base, Changes.model_validate_json(raw))


def _staged(run: _Run, messages: list[Message], decode: Callable[[str], Design]) -> Generator[Step, None, str | None]:
    # a dense drawing in one answer takes many minutes and drops details; stages keep each answer short
    budget = THINKING_BUDGET[run.thinking] if run.thinking else None
    raw = run.llm.chat([*messages, Message(role="user", content=PLAN_NOTE)], StagePlan.model_json_schema(), run.seed, 0.0, budget)
    try:
        stages = StagePlan.model_validate_json(raw).stages
    except ValidationError:
        return None
    if len(stages) < 2:
        return None
    yield Step(kind="plan", message="; ".join(f"{i}. {s.name}" for i, s in enumerate(stages, 1)), attempt=0, elapsed_ms=run.clock())
    design: Design | None = None
    for number, stage in enumerate(stages, 1):
        history = messages if design is None else [*messages, Message(role="assistant", content=answer_json(design))]
        prompt = [*history, Message(role="user", content=stage_message(stage, number, len(stages)))]
        schema = json_schema() if design is None else Changes.model_json_schema()
        for _ in range(STAGE_TRIES):
            answer = run.llm.chat(prompt, schema, run.seed, 0.0, budget)
            candidate, problems = _stage_build(answer, design, decode, run.build, run.out_dir / f"stage_{number}")
            if not problems:
                design = candidate
                break
            prompt = [*prompt, Message(role="assistant", content=answer), Message(role="user", content=stage_repair(problems, number))]
        done = "built" if not problems else "left out: " + "; ".join(problems[:3])
        yield Step(kind="build", message=f"stage {number}, {stage.name}: {done}", attempt=0, elapsed_ms=run.clock())
    return answer_json(design) if design else None


def _stage_build(
    answer: str, design: Design | None, decode: Callable[[str], Design], build: Build, out_dir: Path
) -> tuple[Design | None, list[str]]:
    try:
        candidate = decode(answer) if design is None else merged(design, Changes.model_validate_json(answer))
    except ValidationError as e:
        return None, [f"{_where(answer, err['loc'])}: {err['msg']}" for err in e.errors()[:8]]
    except ValueError as e:
        return None, [str(e)]
    # parameters a later stage will use are not unused yet
    errors = [str(e) for e in validate(candidate) if "defined but not used" not in e.message]
    if errors:
        return None, errors[:8]
    try:
        build(candidate, out_dir)
    except BuildError as e:
        return None, [_kernel_text(e)]
    return candidate, []


def evaluate(
    raw: str, decode: Callable[[str], Design], reqs: list[Requirement], build: Build, out_dir: Path, request: str = ""
) -> tuple[list[str], Design | None, Artifact | None, list[CheckResult]]:
    try:
        design = drop_unused_params(normalize(decode(raw)))
    except ValidationError as e:
        return [f"{_where(raw, err['loc'])}: {err['msg']}" for err in e.errors()[:8]], None, None, []
    except (ParamError, ComponentError, ValueError) as e:
        return [str(e)], None, None, []
    design = unquote(design, request) if request else design
    errors = validate(design)
    if errors:
        return [str(e) for e in errors[:8]], design, None, []
    try:
        artifact = build(design, out_dir)
    except BuildError as e:
        return [_kernel_text(e)], design, None, []
    checks = check(reqs, artifact)
    problems = [_finding_text(f) for f in artifact.findings if f.severity == "error" or f.rule_id == SKIPPED]
    problems += [f"requirement not met: {c.requirement.description} (actual: {c.actual})" for c in checks if not c.passed]
    return list(dict.fromkeys(problems)), design, artifact, checks


def _where(raw: str, loc: tuple[int | str, ...]) -> str:
    # list positions become the ids the model wrote, so "parts.0.features.3" reads "parts.bracket.features.bolt_holes"
    try:
        node: Any = json.loads(raw)
    except ValueError:
        return ".".join(map(str, loc))
    out = []
    for key in loc:
        if isinstance(node, list) and isinstance(key, int) and key < len(node):
            node = node[key]
        else:
            node = node.get(key) if isinstance(node, dict) else None
        ident = node.get("id") if isinstance(key, int) and isinstance(node, dict) else None
        out.append(str(ident or key))
    return ".".join(out)


def _kernel_text(e: BuildError) -> str:
    text = _short(e)
    # failures the compiler explains already name each feature and the fix; only raw kernel errors get a general hint
    if text.startswith("ValueError: feature '"):
        return "The part did not build: " + text.removeprefix("ValueError: ")
    where = f" in feature {e.feature!r}" if e.feature else ""
    hint = " The operation is impossible with the given sketch or dimensions; rethink that feature." if e.kind == "kernel" else ""
    return f"CAD kernel error ({e.kind}){where}: {text}.{hint}"


def _finding_text(f: Finding) -> str:
    fix = f" Fix: {f.suggestion}." if f.suggestion else ""
    where = f" {f.part}" if f.part else ""
    return f"{f.rule_id}{where}: {f.message}.{fix}"


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
