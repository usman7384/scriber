import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import structlog

from partwright_agent import Grounding, Result, overall_size
from partwright_agent import Step as AgentStep
from partwright_agent import generate as agent_generate
from partwright_agent import refine as agent_refine
from partwright_api import disk, repo
from partwright_api.deps import Deps
from partwright_api.jobs import Emit, Outcome
from partwright_api.schemas import Check, GenerateIn, Metrics, Origin, Param, RefineIn, Step, VersionData
from partwright_api.views import model_urls
from partwright_geometry import Artifact, BuildError
from partwright_ir import Design, Process, ShapeDescriptor, apply_params, diff, label

log = structlog.get_logger()


def generate(d: Deps, project_id: str, model_id: str, req: GenerateIn, emit: Emit) -> Outcome:
    only = None if req.context_ids is None else docs(d, req.context_ids)
    context = ground(d, project_id, req.prompt, req.process, only, docs(d, req.attachments))
    number, out = allocate(d, model_id)
    steps = agent_generate(req.prompt, d.llm, d.geometry, out, d.settings.max_repairs, d.settings.seed, context)
    return finish(d, project_id, model_id, number, relay(steps, emit), Meta("generate", req.prompt, req.process, req.attachments))


def refine(d: Deps, project_id: str, model_id: str, req: RefineIn, emit: Emit) -> Outcome:
    base_number, base = latest_ok(d, model_id)
    design = disk.design(disk.version_dir(d.settings.data_dir, model_id, base_number))
    process = req.process or base.process
    context = ground(d, project_id, req.instruction, process, None, docs(d, req.attachments))
    number, out = allocate(d, model_id)
    steps = agent_refine(design, req.instruction, d.llm, d.geometry, out, d.settings.max_repairs, d.settings.seed, context, req.target)
    return finish(d, project_id, model_id, number, relay(steps, emit), Meta("refine", req.instruction, process, req.attachments, design))


def rebuild(d: Deps, project_id: str, model_id: str, values: Mapping[str, float], origin: Origin, emit: Emit) -> Outcome:
    base_number, base = latest_ok(d, model_id)
    previous = disk.design(disk.version_dir(d.settings.data_dir, model_id, base_number))
    design = apply_params(previous, values)
    with d.context_lock:
        rules = d.context.rules(project_id)
    number, out = allocate(d, model_id)
    start = time.monotonic()
    artifact: Artifact | None = None
    try:
        artifact = d.geometry.build(design, out, rules, base.process)
        errors = [f"{f.rule_id}: {f.message}" for f in artifact.findings if f.severity == "error"]
        message = "; ".join([f"rebuilt in {artifact.elapsed_ms} ms", *errors])
    except BuildError as e:
        message = f"CAD kernel error ({e.kind}): {e}"
    result = Result(design=design, artifact=artifact, checks=[], attempts=1, repairs=0, used=base.used)
    kind = "done" if result.ok else "failed"
    step = AgentStep(kind=kind, message=message, attempt=1, elapsed_ms=int((time.monotonic() - start) * 1000), result=result)
    prompt = ", ".join(f"{k}={v:g}" for k, v in values.items())
    return finish(d, project_id, model_id, number, relay([step], emit), Meta(origin, prompt, base.process, [], previous))


def ground(d: Deps, project_id: str, request: str, process: Process, only: list[str] | None, attached: list[str]) -> Grounding:
    with d.context_lock:
        pack = d.context.retrieve(project_id, request)
        rules = d.context.rules(project_id)
        extra = [f for doc in attached for f in d.context.facts(project_id, doc)]
    if only is not None:
        keep = {*only, *attached}
        pack = pack.model_copy(
            update={
                "chunks": [c for c in pack.chunks if c.doc_id in keep],
                "facts": [f for f in pack.facts if f.doc_id in keep],
                "conventions": [f for f in pack.conventions if f.doc_id in keep],
            }
        )
    facts = list({f.id: f for f in [*pack.facts, *extra]}.values())
    return Grounding(pack=pack.model_copy(update={"facts": facts}), rules=rules, process=process)


def docs(d: Deps, file_ids: list[str]) -> list[str]:
    rows = [repo.file_row(d.engine, i) for i in file_ids]
    return [r["doc_id"] for r in rows if r and r["doc_id"]]


def latest_ok(d: Deps, model_id: str) -> tuple[int, VersionData]:
    ok = [(n, v) for n, v in repo.versions(d.engine, model_id) if v.status == "ok"]
    if not ok:
        raise LookupError(f"model {model_id} has no successful version")
    return ok[-1]


def allocate(d: Deps, model_id: str) -> tuple[int, Path]:
    number = disk.next_number(d.settings.data_dir, model_id)
    out = disk.version_dir(d.settings.data_dir, model_id, number)
    out.mkdir(parents=True)
    return number, out


def relay(steps: Iterable[AgentStep], emit: Emit) -> list[AgentStep]:
    seen = []
    for s in steps:
        seen.append(s)
        emit(Step(kind=s.kind, message=s.message, attempt=s.attempt, elapsed_ms=s.elapsed_ms))
    return seen


@dataclass(frozen=True)
class Meta:
    origin: Origin
    prompt: str | None
    process: Process
    attachments: list[str]
    previous: Design | None = None


def finish(d: Deps, project_id: str, model_id: str, number: int, steps: list[AgentStep], meta: Meta) -> Outcome:
    out = disk.version_dir(d.settings.data_dir, model_id, number)
    result = steps[-1].result if steps else None
    disk.save(out, steps, result)
    data = version_data(result, meta, thumbnail(d, out))
    repo.add_version(d.engine, model_id, number, data)
    if result is None or result.design is None or data.status != "ok":
        return Outcome(version=number, error=steps[-1].message if steps else "no result")
    repo.set_model(d.engine, model_id, title=result.design.title, stale=False)
    record(d, project_id, model_id, number, result)
    return Outcome(version=number, events=(("version.created", created_payload(d, model_id, number)),))


def record(d: Deps, project_id: str, model_id: str, number: int, result: Result) -> None:
    assert result.design is not None
    out = disk.version_dir(d.settings.data_dir, model_id, number)
    shapes: dict[str, ShapeDescriptor] = {}
    if len(result.design.parts) == 1:
        shapes[result.design.parts[0].id] = d.geometry.describe(out / disk.FILE_NAMES["step"])
    with d.context_lock:
        d.context.record_generation(project_id, graph_id(model_id, number), result.design, result.used, shapes)


def graph_id(model_id: str, number: int) -> str:
    return f"{model_id}/v{number}"


def created_payload(d: Deps, model_id: str, number: int) -> dict[str, object]:
    urls = model_urls(model_id, number)
    return {"model_id": model_id, "version": number, "files": {k: d.settings.public_url + urls(k) for k in disk.FILE_NAMES}}


def thumbnail(d: Deps, out: Path) -> bool:
    glb = out / disk.FILE_NAMES["glb"]
    if not glb.exists():
        return False
    try:
        d.geometry.thumbnail(glb, out / disk.THUMBNAIL)
    except BuildError as e:
        log.warning("thumbnail_unavailable", error=str(e))
        return False
    return True


def version_data(result: Result | None, meta: Meta, has_thumbnail: bool) -> VersionData:
    base = VersionData(
        created=repo.now(), status="failed", origin=meta.origin, prompt=meta.prompt, process=meta.process, attachments=meta.attachments
    )
    if result is None or result.design is None:
        return base
    art = result.artifact
    return base.model_copy(
        update={
            "status": "ok" if result.ok else "failed",
            "params": [Param(label=label(p.name), **p.model_dump()) for p in result.design.params],
            "checks": [Check(description=c.requirement.description, passed=c.passed, actual=c.actual) for c in result.checks],
            "findings": art.findings if art else [],
            "metrics": metrics(art) if art else None,
            "used": result.used,
            "thumbnail": has_thumbnail,
            "changes": diff(meta.previous, result.design) if meta.previous else None,
        }
    )


def metrics(art: Artifact) -> Metrics:
    masses = [p.mass_g for p in art.parts]
    mass = None if any(m is None for m in masses) else sum(m for m in masses if m is not None)
    return Metrics(bbox=overall_size(art), volume=sum(p.volume for p in art.parts), mass_g=mass, holes=sum(len(p.holes) for p in art.parts))
