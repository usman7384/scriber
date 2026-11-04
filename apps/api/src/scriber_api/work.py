import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from scriber_agent import Grounding, Result, overall_size
from scriber_agent import Step as AgentStep
from scriber_agent import generate as agent_generate
from scriber_agent import refine as agent_refine
from scriber_api import disk, repo
from scriber_api.deps import Deps
from scriber_api.jobs import Emit, Outcome
from scriber_api.schemas import Check, GenerateIn, Input, Metrics, Origin, Param, RefineIn, Step, VersionData
from scriber_api.views import model_urls
from scriber_geometry import Artifact, BuildError
from scriber_ir import Design, Process, Provenance, ShapeDescriptor, apply_params, diff, label

log = structlog.get_logger()
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
PROGRESS = {"requirements": 10, "emit": 40, "check": 60, "repair": 70, "done": 100, "failed": 100}


@dataclass(frozen=True)
class Rebuild:
    values: Mapping[str, float]
    origin: Origin
    note: str | None = None
    sources: Mapping[str, Provenance] = field(default_factory=dict)
    # variants build from another model's latest design
    source_id: str | None = None
    # a replaced document gives its facts new ids; lineage follows them
    relink: Mapping[str, str] = field(default_factory=dict)
    materials: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Meta:
    origin: Origin
    prompt: str | None
    process: Process
    attachments: list[str]
    images: list[str]
    previous: Design | None = None


def generate(d: Deps, project_id: str, model_id: str, req: GenerateIn, emit: Emit) -> Outcome:
    only = None if req.context_ids is None else docs(d, req.context_ids)
    context = ground(d, project_id, req.prompt, req.process, only, docs(d, req.attachments))
    images = image_files(d, project_id, req.attachments)
    number, out = allocate(d, model_id)
    steps = agent_generate(
        req.prompt,
        d.llm,
        d.geometry,
        out,
        d.settings.max_repairs,
        d.settings.seed,
        context,
        tuple(images.values()),
        req.thinking,
        vision=d.vision,
    )
    meta = Meta("generate", req.prompt, req.process, req.attachments, list(images))
    return finish(d, project_id, model_id, number, relay(steps, emit), meta)


def refine(d: Deps, project_id: str, model_id: str, req: RefineIn, emit: Emit, origin: Origin = "refine") -> Outcome:
    base_number, base = latest_ok(d, model_id)
    design = disk.design(disk.version_dir(d.settings.data_dir, model_id, base_number))
    process = req.process or base.process
    context = ground(d, project_id, req.instruction, process, None, docs(d, req.attachments))
    images = image_files(d, project_id, req.attachments)
    number, out = allocate(d, model_id)
    images_sent = tuple(images.values())
    steps = agent_refine(
        design, req.instruction, d.llm, d.geometry, out, d.settings.max_repairs, d.settings.seed, context, images_sent, d.vision, req.target
    )
    meta = Meta(origin, req.instruction, process, req.attachments, list(images), design)
    return finish(d, project_id, model_id, number, relay(steps, emit), meta)


def rebuild(d: Deps, project_id: str, model_id: str, edit: Rebuild, emit: Emit) -> Outcome:
    source = edit.source_id or model_id
    base_number, base = latest_ok(d, source)
    previous = disk.design(disk.version_dir(d.settings.data_dir, source, base_number))
    design = previous
    for name, value in edit.values.items():
        design = apply_params(design, {name: value}, edit.sources.get(name))
    if edit.materials:
        design = with_materials(design, edit.materials)
    used = live(d, project_id, [edit.relink.get(u, u) for u in base.used])
    prompt = edit.note or ", ".join(f"{k}={v:g}" for k, v in edit.values.items())
    return build(d, project_id, model_id, design, Meta(edit.origin, prompt, base.process, [], [], previous), emit, used)


def build(d: Deps, project_id: str, model_id: str, design: Design, meta: Meta, emit: Emit, used: list[str] | None = None) -> Outcome:
    with d.context_lock:
        rules = d.context.rules(project_id)
    number, out = allocate(d, model_id)
    start = time.monotonic()
    artifact: Artifact | None = None
    try:
        artifact = d.geometry.build(design, out, rules, meta.process)
        errors = [f"{f.rule_id}: {f.message}" for f in artifact.findings if f.severity == "error"]
        message = "; ".join([f"built in {artifact.elapsed_ms} ms", *errors])
    except BuildError as e:
        message = f"CAD kernel error ({e.kind}): {e}"
    result = Result(design=design, artifact=artifact, checks=[], attempts=1, repairs=0, used=used or [])
    kind = "done" if result.ok else "failed"
    step = AgentStep(kind=kind, message=message, attempt=1, elapsed_ms=int((time.monotonic() - start) * 1000), result=result)
    return finish(d, project_id, model_id, number, relay([step], emit), meta)


def with_materials(design: Design, materials: Mapping[str, str]) -> Design:
    parts = [p.model_copy(update={"material": materials.get(p.id, p.material)}) for p in design.parts]
    return design.model_copy(update={"parts": parts})


def ground(d: Deps, project_id: str, request: str, process: Process, only: list[str] | None, attached: list[str]) -> Grounding:
    with d.context_lock:
        pack = d.context.retrieve(project_id, request)
        rules = d.context.rules(project_id)
        extra = [f for doc in [*attached, *(only or [])] for f in d.context.facts(project_id, doc)]
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


def image_files(d: Deps, project_id: str, file_ids: list[str]) -> dict[str, bytes]:
    rows = [r for r in (repo.file_row(d.engine, i) for i in file_ids) if r and r["name"].lower().endswith(IMAGE_SUFFIXES)]
    return {r["id"]: disk.upload_path(d.settings.data_dir, project_id, r["id"], r["name"]).read_bytes() for r in rows}


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
    seen: list[AgentStep] = []
    progress = 0
    for s in steps:
        seen.append(s)
        progress = max(progress, PROGRESS.get(s.kind, progress))
        emit(Step(kind=s.kind, message=s.message, attempt=s.attempt, elapsed_ms=s.elapsed_ms, progress=progress))
    return seen


def finish(d: Deps, project_id: str, model_id: str, number: int, steps: list[AgentStep], meta: Meta) -> Outcome:
    out = disk.version_dir(d.settings.data_dir, model_id, number)
    result = steps[-1].result if steps else None
    disk.save(out, steps, result)
    data = version_data(result, meta, thumbnail(d, out)).model_copy(update={"inputs": inputs(d, project_id, meta, result)})
    repo.add_version(d.engine, model_id, number, data)
    if result is None or result.design is None or data.status != "ok":
        return Outcome(version=number, error=steps[-1].message if steps else "no result")
    repo.set_model(d.engine, model_id, title=result.design.title, stale=False)
    record(d, project_id, model_id, number, result)
    return Outcome(version=number, events=(("version.created", created_payload(d, model_id, number)),))


def live(d: Deps, project_id: str, used: list[str]) -> list[str]:
    with d.context_lock:
        known = {n.id for n in d.context.graph(project_id).nodes} | {r.id for r in d.context.rules(project_id).rules}
    return [u for u in used if u in known]


def record(d: Deps, project_id: str, model_id: str, number: int, result: Result) -> None:
    assert result.design is not None
    out = disk.version_dir(d.settings.data_dir, model_id, number)
    shapes: dict[str, ShapeDescriptor] = {}
    if len(result.design.parts) == 1:
        shapes[result.design.parts[0].id] = d.geometry.describe(out / disk.FILE_NAMES["step"])
    with d.context_lock:
        d.context.record_generation(project_id, graph_id(model_id, number), result.design, result.used, shapes)


def inputs(d: Deps, project_id: str, meta: Meta, result: Result | None) -> list[Input]:
    rows = {r["id"]: r for r in repo.file_rows(d.engine, project_id)}
    with d.context_lock:
        fact_docs = {f.id: f.doc_id for f in d.context.facts(project_id)}
    used_docs = {fact_docs.get(u, u) for u in (result.used if result else [])}
    used = {i for i, r in rows.items() if r["doc_id"] in used_docs or i in meta.images}
    listed = [i for i in dict.fromkeys([*meta.attachments, *(i for i in rows if i in used)]) if i in rows]
    files = [Input(kind="file", id=i, name=rows[i]["name"], role="used" if i in used else "unused") for i in listed]
    return [Input(kind="prompt", role="used"), *files] if meta.prompt else files


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
