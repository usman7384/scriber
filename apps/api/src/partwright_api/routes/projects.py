from fastapi import APIRouter, Depends

from partwright_api import repo, views
from partwright_api.auth import require_token
from partwright_api.deps import DepsDep
from partwright_api.routes.common import need_ollama, need_project, start_generate
from partwright_api.schemas import Batch, BatchIn, GenerateIn, Job, Model, Project, ProjectIn

router = APIRouter(dependencies=[Depends(require_token)])


@router.post("/projects", status_code=201)
def create_project(body: ProjectIn, d: DepsDep) -> Project:
    return repo.create_project(d.engine, body.name)


@router.get("/projects")
def list_projects(d: DepsDep) -> list[Project]:
    return repo.projects(d.engine)


@router.get("/projects/{project_id}")
def get_project(project_id: str, d: DepsDep) -> Project:
    return need_project(d, project_id)


@router.post("/projects/{project_id}/generate", status_code=202)
async def generate(project_id: str, body: GenerateIn, d: DepsDep) -> Job:
    need_project(d, project_id)
    await need_ollama(d)
    return start_generate(d, project_id, body)


@router.get("/projects/{project_id}/models")
def list_models(project_id: str, d: DepsDep) -> list[Model]:
    need_project(d, project_id)
    return [views.model(row, repo.versions(d.engine, row["id"])) for row in repo.model_rows(d.engine, project_id)]


@router.post("/batch", status_code=202)
async def batch(body: BatchIn, d: DepsDep) -> Batch:
    need_project(d, body.project_id)
    await need_ollama(d)
    return Batch(jobs=[start_generate(d, body.project_id, GenerateIn(prompt=p, process=body.process)) for p in body.prompts])
