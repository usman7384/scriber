import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from partwright_api import disk, repo, views, work
from partwright_api.auth import require_token
from partwright_api.deps import Deps, DepsDep
from partwright_api.repo import Row
from partwright_api.routes.common import (
    export,
    latest_design,
    need_idle,
    need_model,
    need_ollama,
    need_version,
    start_rebuild,
    start_refine,
)
from partwright_api.schemas import Component, FileKind, Job, ModelDetail, ParamsIn, RefineIn, Version
from partwright_ir import diff, joint_tree

router = APIRouter(prefix="/models/{model_id}", dependencies=[Depends(require_token)])


@router.get("")
def get_model(model_id: str, d: DepsDep) -> ModelDetail:
    return detail(d, need_model(d, model_id))


@router.get("/versions")
def list_versions(model_id: str, d: DepsDep) -> list[Version]:
    need_model(d, model_id)
    return [views.version(model_id, n, v, views.model_urls(model_id, n)) for n, v in repo.versions(d.engine, model_id)]


@router.get("/versions/{number}")
def get_version(model_id: str, number: int, d: DepsDep) -> Version:
    need_model(d, model_id)
    n, data = need_version(d, model_id, number)
    return views.version(model_id, n, data, views.model_urls(model_id, n))


@router.get("/versions/{number}/thumbnail")
def thumbnail(model_id: str, number: int, d: DepsDep) -> FileResponse:
    return thumbnail_file(d, model_id, number)


@router.post("/versions/{number}/restore", status_code=201)
async def restore(model_id: str, number: int, d: DepsDep) -> Version:
    model = need_model(d, model_id)
    need_idle(d, model_id)
    n, data = need_version(d, model_id, number)
    if data.status != "ok":
        raise HTTPException(400, f"version {n} failed and cannot be restored")
    new = await asyncio.to_thread(_restore, d, model, n)
    d.hooks.fire("version.created", work.created_payload(d, model_id, new))
    return get_version(model_id, new, d)


@router.post("/refine", status_code=202)
async def refine(model_id: str, body: RefineIn, d: DepsDep) -> Job:
    model = need_model(d, model_id)
    await need_ollama(d)
    return start_refine(d, model, body)


@router.patch("/params", status_code=202)
async def params(model_id: str, body: ParamsIn, d: DepsDep) -> Job:
    return start_rebuild(d, need_model(d, model_id), body.values, "params", "params")


@router.get("/export")
def export_file(model_id: str, d: DepsDep, fmt: FileKind = "step", version: int | None = None) -> FileResponse:
    return export(d, need_model(d, model_id), fmt, version)


@router.get("/components")
def components(model_id: str, d: DepsDep, version: int | None = None) -> list[Component]:
    need_model(d, model_id)
    n, data = need_version(d, model_id, version)
    if data.status != "ok":
        raise HTTPException(404, f"version {n} of model {model_id} failed and has no components")
    design = disk.design(disk.version_dir(d.settings.data_dir, model_id, n))
    placed = {child: (joint.id, parent) for child, (joint, parent) in joint_tree(design).items()}
    rows = [(p, *placed.get(p.id, (None, None))) for p in design.parts]
    return [Component(id=p.id, name=p.name, material=p.material, joint=joint, parent=parent) for p, joint, parent in rows]


def detail(d: Deps, model: Row) -> ModelDetail:
    versions = repo.versions(d.engine, model["id"])
    latest = [views.version(model["id"], n, v, views.model_urls(model["id"], n)) for n, v in versions[-1:]]
    return ModelDetail(**views.model(model, versions).model_dump(), version=latest[0] if latest else None)


def thumbnail_file(d: Deps, model_id: str, number: int) -> FileResponse:
    path = disk.version_dir(d.settings.data_dir, model_id, number) / disk.THUMBNAIL
    if not path.exists():
        raise HTTPException(404, f"version {number} of model {model_id} has no thumbnail")
    return FileResponse(path, media_type="image/png")


def _restore(d: Deps, model: Row, number: int) -> int:
    model_id = model["id"]
    src = disk.version_dir(d.settings.data_dir, model_id, number)
    current, design = latest_design(d, model_id), disk.design(src)
    new = disk.next_number(d.settings.data_dir, model_id)
    disk.copy_version(src, disk.version_dir(d.settings.data_dir, model_id, new))
    data = repo.version(d.engine, model_id, number)
    assert data is not None
    restored = data.model_copy(update={"origin": "restore", "created": repo.now(), "changes": diff(current, design)})
    repo.add_version(d.engine, model_id, new, restored)
    repo.set_model(d.engine, model_id, title=design.title, stale=False)
    with d.context_lock:
        d.context.record_generation(model["project_id"], work.graph_id(model_id, new), design, data.used)
    return new
