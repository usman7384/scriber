import re
from collections.abc import Mapping
from functools import partial

import httpx
from fastapi import HTTPException
from fastapi.responses import FileResponse

from partwright_api import disk, jobs_db, repo, work
from partwright_api.deps import Deps
from partwright_api.repo import Row
from partwright_api.schemas import FileKind, GenerateIn, Job, JobKind, Origin, Project, RefineIn, VersionData
from partwright_api.work import Rebuild
from partwright_context import Fact
from partwright_ir import Design, ParamError, apply_params, drop_unused_params


def need_project(d: Deps, project_id: str) -> Project:
    project = repo.project(d.engine, project_id)
    if project is None:
        raise HTTPException(404, f"project {project_id} not found")
    return project


def need_model(d: Deps, model_id: str) -> Row:
    row = repo.model_row(d.engine, model_id)
    if row is None:
        raise HTTPException(404, f"model {model_id} not found")
    return row


def need_version(d: Deps, model_id: str, number: int | None = None) -> tuple[int, VersionData]:
    versions = repo.versions(d.engine, model_id)
    found = versions[-1:] if number is None else [(n, v) for n, v in versions if n == number]
    if not found:
        raise HTTPException(404, f"model {model_id} has no version {number or ''}".rstrip())
    return found[0]


def need_file(d: Deps, project_id: str, file_id: str) -> Row:
    row = repo.file_row(d.engine, file_id)
    if row is None or row["project_id"] != project_id:
        raise HTTPException(404, f"file {file_id} not found in project {project_id}")
    return row


def need_processed(d: Deps, project_id: str, file_ids: list[str]) -> None:
    for file_id in file_ids:
        row = repo.file_row(d.engine, file_id)
        if row is None or row["project_id"] != project_id or row["status"] != "processed":
            raise HTTPException(400, f"file {file_id} is not a processed file of project {project_id}")


def need_idle(d: Deps, model_id: str) -> None:
    if jobs_db.busy(d.engine, model_id):
        raise HTTPException(409, f"a job for model {model_id} is still running")


async def need_ollama(d: Deps) -> None:
    if d.settings.ollama_host and not await ollama_up(d):
        raise HTTPException(503, f"Ollama is not reachable at {d.settings.ollama_host}")


async def ollama_up(d: Deps) -> bool:
    if not d.settings.ollama_host:
        return False
    try:
        response = await d.http.get(f"{d.settings.ollama_host}/api/version", timeout=2)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


def latest_design(d: Deps, model_id: str) -> Design:
    ok = [n for n, v in repo.versions(d.engine, model_id) if v.status == "ok"]
    if not ok:
        raise HTTPException(400, f"model {model_id} has no successful version")
    return disk.design(disk.version_dir(d.settings.data_dir, model_id, ok[-1]))


def start_generate(d: Deps, project_id: str, req: GenerateIn) -> Job:
    need_processed(d, project_id, [*(req.context_ids or []), *req.attachments])
    model_id = repo.create_model(d.engine, project_id, req.prompt)
    run = partial(work.generate, d, project_id, model_id, req)
    return d.jobs.submit("generate", project_id, model_id, run, req.model_dump(mode="json"))


def start_refine(d: Deps, model: Row, req: RefineIn, origin: Origin = "refine") -> Job:
    model_id, project_id = model["id"], model["project_id"]
    need_idle(d, model_id)
    design = latest_design(d, model_id)
    if req.target is not None and req.target not in {p.id for p in design.parts}:
        raise HTTPException(400, f"unknown part {req.target!r}; parts: {sorted(p.id for p in design.parts)}")
    need_processed(d, project_id, req.attachments)
    run = partial(work.refine, d, project_id, model_id, req, origin=origin)
    return d.jobs.submit("refine", project_id, model_id, run, req.model_dump(mode="json"))


def start_rebuild(d: Deps, model: Row, edit: Rebuild, kind: JobKind) -> Job:
    model_id, project_id = model["id"], model["project_id"]
    need_idle(d, model_id)
    try:
        apply_params(latest_design(d, edit.source_id or model_id), edit.values)
    except ParamError as e:
        raise HTTPException(400, str(e)) from None
    run = partial(work.rebuild, d, project_id, model_id, edit)
    return d.jobs.submit(kind, project_id, model_id, run, {"values": dict(edit.values), "origin": edit.origin})


def start_variant(d: Deps, base: Row, param: str, value: float) -> Job:
    model_id = repo.create_model(d.engine, base["project_id"], f"{base['title']} ({param} {value:g})")
    model = need_model(d, model_id)
    return start_rebuild(d, model, Rebuild({param: value}, "variant", source_id=base["id"]), "params")


def follow_spec(d: Deps, model_id: str, file_name: str, pairs: list[tuple[Fact, Fact]], relink: Mapping[str, str]) -> Job:
    model = need_model(d, model_id)
    note = f"{file_name} changed: " + "; ".join(f"{new.name} {_v(old.value)} -> {_v(new.value)} {new.unit}".rstrip() for old, new in pairs)
    by_ref = {old.source.ref: new for old, new in pairs if old.source.ref and isinstance(new.value, float)}
    cited = {p.name: by_ref[p.provenance.ref] for p in latest_design(d, model_id).params if p.provenance.ref in by_ref}
    if {f.id for f in cited.values()} == {new.id for _, new in pairs}:
        values = {n: float(f.value) for n, f in cited.items()}
        edit = Rebuild(values, "context", note, {n: f.source for n, f in cited.items()}, relink=relink)
        return start_rebuild(d, model, edit, "params")
    return start_refine(d, model, RefineIn(instruction=f"{note}. Update the design to match."), "context")


def _v(value: float | str) -> str:
    return f"{value:g}" if isinstance(value, float) else value


def component_only(design: Design, component_id: str, names: set[str]) -> None:
    parts = {p.id: p for p in design.parts}
    if component_id not in parts:
        raise HTTPException(400, f"unknown component {component_id!r}; components: {sorted(parts)}")

    def used_by(part_id: str) -> set[str]:
        return {p.name for p in drop_unused_params(design.model_copy(update={"parts": [parts[part_id]]})).params}

    others = set().union(*(used_by(i) for i in parts if i != component_id))
    foreign = sorted(n for n in names if n not in used_by(component_id) or n in others)
    if foreign:
        raise HTTPException(400, f"parameters {foreign} do not belong to component {component_id!r} alone")


def export(d: Deps, model: Row, fmt: FileKind, number: int | None) -> FileResponse:
    n, data = need_version(d, model["id"], number)
    path = disk.version_dir(d.settings.data_dir, model["id"], n) / disk.FILE_NAMES[fmt]
    if data.metrics is None or not path.exists():
        raise HTTPException(404, f"version {n} of model {model['id']} has no {fmt} file")
    name = f"{re.sub(r'[^a-z0-9]+', '-', model['title'].lower()).strip('-') or 'model'}-v{n}{path.suffix}"
    return FileResponse(path, media_type=disk.MEDIA_TYPES[fmt], filename=name)
