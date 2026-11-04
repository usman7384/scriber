from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from scriber_api import repo
from scriber_api.auth import User, require_token
from scriber_api.deps import Deps, DepsDep
from scriber_api.routes.common import (
    component_only,
    export,
    latest_design,
    need_model,
    need_ollama,
    start_generate,
    start_rebuild,
    start_refine,
)
from scriber_api.schemas import DownloadV1, EditV1, GenerateIn, GenerateV1, JobRef, ModifyV1, RefineIn
from scriber_api.work import Rebuild

DEFAULT_PROJECT = "default"
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_token)])


@router.post("/generate", status_code=202)
async def generate(body: GenerateV1, d: DepsDep, user: User) -> JobRef:
    await need_ollama(d)
    attachments = [i for i in (body.image, body.mesh) if i]
    job = start_generate(d, default_project(d), GenerateIn(prompt=body.prompt, attachments=attachments), user)
    return JobRef(job_id=job.id)


@router.post("/modify", status_code=202)
async def modify(body: ModifyV1, d: DepsDep, user: User) -> JobRef:
    await need_ollama(d)
    job = start_refine(d, need_model(d, body.model_id), RefineIn(instruction=body.prompt, attachments=body.attachments), user=user)
    return JobRef(job_id=job.id)


@router.post("/edit", status_code=202)
async def edit(body: EditV1, d: DepsDep) -> JobRef:
    model = need_model(d, body.model_id)
    component_only(latest_design(d, body.model_id), body.component_id, set(body.params))
    return JobRef(job_id=start_rebuild(d, model, Rebuild(body.params, "edit"), "edit").id)


@router.post("/download")
def download(body: DownloadV1, d: DepsDep) -> FileResponse:
    return export(d, need_model(d, body.model_id), body.format, None)


def default_project(d: Deps) -> str:
    if repo.project(d.engine, DEFAULT_PROJECT) is None:
        repo.create_project(d.engine, "Default", DEFAULT_PROJECT)
    return DEFAULT_PROJECT
