import asyncio
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from scriber_api import disk, ingest, repo, schemas, views
from scriber_api.auth import require_token
from scriber_api.deps import DepsDep
from scriber_api.routes.common import need_file, need_ollama, need_project
from scriber_api.schemas import ContextListing, GraphView, Job
from scriber_context import GraphView as ContextGraph
from scriber_ir import Provenance, Rule

router = APIRouter(prefix="/projects/{project_id}", dependencies=[Depends(require_token)])


@router.post("/context", status_code=202)
async def upload(
    project_id: str,
    d: DepsDep,
    files: Annotated[list[UploadFile], File(default_factory=list)],
    bracketed: Annotated[list[UploadFile], File(default_factory=list, alias="files[]")],
) -> list[Job]:
    need_project(d, project_id)
    # docs/API.md and the web client name the field files[]; scripts and the CLI send files
    if not files and not bracketed:
        raise HTTPException(422, "send the files as multipart field files[]")
    await need_ollama(d)
    jobs = []
    for upload in [*files, *bracketed]:
        name = Path(upload.filename or "").name
        if not name:
            raise HTTPException(400, "every uploaded file needs a name")
        file_id = repo.add_file(d.engine, project_id, name)
        path = disk.upload_path(d.settings.data_dir, project_id, file_id, name)
        path.parent.mkdir(parents=True)
        path.write_bytes(await upload.read())
        jobs.append(d.jobs.submit("ingest", project_id, None, partial(ingest.ingest, d, project_id, file_id, path)))
    return jobs


@router.get("/context")
def listing(project_id: str, d: DepsDep) -> ContextListing:
    need_project(d, project_id)
    with d.context_lock:
        docs = {doc.id: doc for doc in d.context.documents(project_id)}
        graph = d.context.graph(project_id)
        stats = d.context.stats(project_id)
    used_in = _used_in(graph)
    rows = repo.file_rows(d.engine, project_id)
    files = [views.file(r, docs.get(r["doc_id"]), used_in.get(r["doc_id"], [])) for r in rows]
    stale = [m["id"] for m in repo.model_rows(d.engine, project_id) if m["stale"]]
    return ContextListing(files=files, stats=stats, stale=stale)


@router.get("/context/{file_id}/facts")
def facts(project_id: str, file_id: str, d: DepsDep) -> list[schemas.Fact]:
    row = need_file(d, project_id, file_id)
    if row["doc_id"] is None:
        return []
    with d.context_lock:
        found = d.context.facts(project_id, row["doc_id"])
    return [views.fact(f, file_id) for f in found]


@router.delete("/context/{file_id}", status_code=204)
async def delete(project_id: str, file_id: str, d: DepsDep) -> Response:
    row = need_file(d, project_id, file_id)
    if row["status"] == "processing":
        raise HTTPException(409, f"file {file_id} is still being processed")
    for event, payload in await asyncio.to_thread(ingest.remove, d, project_id, row):
        d.hooks.fire(event, payload)
    return Response(status_code=204)


@router.get("/rules")
def rules(project_id: str, d: DepsDep) -> list[schemas.Rule]:
    need_project(d, project_id)
    with d.context_lock:
        return [views.rule(r) for r in d.context.rules(project_id).rules]


@router.put("/rules/{rule_id}")
def set_rule(project_id: str, rule_id: str, body: schemas.Rule, d: DepsDep) -> schemas.Rule:
    need_project(d, project_id)
    if body.id != rule_id:
        raise HTTPException(400, f"rule id {body.id!r} does not match the path {rule_id!r}")
    rule = Rule(**body.model_dump(exclude={"source_ref"}), source=Provenance(source="user_edit", ref=body.source_ref))
    with d.context_lock:
        d.context.set_rule(project_id, rule)
    return views.rule(rule)


@router.get("/graph")
def graph(project_id: str, d: DepsDep) -> GraphView:
    need_project(d, project_id)
    with d.context_lock:
        return GraphView.model_validate(d.context.graph(project_id).model_dump())


def _used_in(graph: ContextGraph) -> dict[str, list[str]]:
    models = {n.id: n.model_id for n in graph.nodes if n.model_id}
    out: dict[str, set[str]] = defaultdict(set)
    for e in graph.edges:
        if e.type == "used_in" and e.dst in models:
            out[e.src].add(models[e.dst].rsplit("/v", 1)[0])
    return {k: sorted(v) for k, v in out.items()}
