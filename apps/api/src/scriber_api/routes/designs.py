from functools import partial
from pathlib import Path
from xml.etree.ElementTree import ParseError

from fastapi import APIRouter, Depends, HTTPException, Request

from scriber_api import disk, repo, work
from scriber_api.auth import require_token
from scriber_api.deps import Deps, DepsDep
from scriber_api.routes.common import need_project
from scriber_api.schemas import DesignIn, Job, Origin
from scriber_api.work import Meta
from scriber_context.aircraft import aircraft_design
from scriber_context.sizing import XmlSizing
from scriber_ir import Design, validate

router = APIRouter(prefix="/projects/{project_id}", dependencies=[Depends(require_token)])


@router.post("/designs", status_code=202)
async def post_design(project_id: str, body: DesignIn, d: DepsDep) -> Job:
    need_project(d, project_id)
    return start_build(d, project_id, body.design, "design", body.prompt)


@router.post("/sizing", status_code=202)
async def post_sizing(project_id: str, request: Request, d: DepsDep, name: str = "sizing.xml") -> Job:
    need_project(d, project_id)
    name = Path(name).name
    if not name.lower().endswith(".xml"):
        raise HTTPException(400, f"sizing file {name!r} must be .xml")
    path = disk.upload_path(d.settings.data_dir, project_id, repo.new_id("x"), name)
    path.parent.mkdir(parents=True)
    path.write_bytes(await request.body())
    try:
        design = aircraft_design(XmlSizing().read(path))
    except (ValueError, ParseError) as e:
        raise HTTPException(400, f"could not read the sizing file: {e}") from None
    return start_build(d, project_id, design, "sizing", f"sizing file {name}")


def start_build(d: Deps, project_id: str, design: Design, origin: Origin, prompt: str | None) -> Job:
    errors = validate(design)
    if errors:
        raise HTTPException(400, "; ".join(map(str, errors[:5])))
    model_id = repo.create_model(d.engine, project_id, design.title)
    run = partial(work.build, d, project_id, model_id, design, Meta(origin, prompt, "any", [], []))
    return d.jobs.submit("build", project_id, model_id, run, {"origin": origin, "prompt": prompt})
