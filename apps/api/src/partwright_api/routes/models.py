import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from partwright_agent import VariantPlan, plan_variants
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
    start_variant,
)
from partwright_api.schemas import Batch, FileKind, Job, ModelDetail, ParamsIn, RefineIn, VariantsIn, Version
from partwright_api.work import Rebuild
from partwright_ir import ParamError, apply_params, diff

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
    return start_rebuild(d, need_model(d, model_id), Rebuild(body.values, "params"), "params")


@router.post("/variants", status_code=202)
async def variants(model_id: str, body: VariantsIn, d: DepsDep) -> Batch:
    model = need_model(d, model_id)
    design = latest_design(d, model_id)
    if body.instruction:
        await need_ollama(d)
        try:
            async with d.jobs.gpu:
                plan = await asyncio.to_thread(plan_variants, design, body.instruction, d.llm, d.settings.seed)
        except ValueError as e:
            raise HTTPException(502, f"could not plan the variants: {e}") from None
    elif body.param and body.values:
        plan = VariantPlan(param=body.param, values=body.values)
    else:
        raise HTTPException(422, "give an instruction, or a param with values")
    try:
        for value in plan.values:
            apply_params(design, {plan.param: value})
    except ParamError as e:
        raise HTTPException(400, str(e)) from None
    return Batch(jobs=[start_variant(d, model, plan.param, v) for v in plan.values])


@router.get("/export")
def export_file(model_id: str, d: DepsDep, fmt: FileKind = "step", version: int | None = None) -> FileResponse:
    return export(d, need_model(d, model_id), fmt, version)


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
    used = work.live(d, model["project_id"], data.used)
    with d.context_lock:
        d.context.record_generation(model["project_id"], work.graph_id(model_id, new), design, used)
    return new
