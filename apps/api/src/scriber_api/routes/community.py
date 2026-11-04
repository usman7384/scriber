import asyncio

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, insert, select

from scriber_api import db, disk, repo, work
from scriber_api.auth import User, require_token
from scriber_api.deps import Deps, DepsDep
from scriber_api.repo import Row
from scriber_api.routes.common import need_model, need_project, need_version
from scriber_api.routes.models import detail
from scriber_api.schemas import ForkIn, ForkSource, ModelDetail, Publication, PublishIn
from scriber_api.views import model_urls

router = APIRouter(prefix="/community", dependencies=[Depends(require_token)])


@router.post("", status_code=201)
def publish(body: PublishIn, d: DepsDep, user: User) -> Publication:
    model = need_model(d, body.model_id)
    n, data = need_version(d, body.model_id, body.version)
    if data.status != "ok":
        raise HTTPException(400, f"version {n} failed and cannot be published")
    row = {"id": repo.new_id("c"), "model_id": model["id"], "version": n, "title": model["title"], "author": user, "created": repo.now()}
    with d.engine.begin() as c:
        c.execute(insert(db.publications).values(**row))
    return _publication(d, row)


@router.get("")
def listing(d: DepsDep) -> list[Publication]:
    with d.engine.connect() as c:
        rows = [dict(r._mapping) for r in c.execute(select(db.publications).order_by(db.publications.c.created.desc()))]
    return [_publication(d, r) for r in rows]


@router.get("/{publication_id}")
def get(publication_id: str, d: DepsDep) -> Publication:
    return _publication(d, _need(d, publication_id))


@router.delete("/{publication_id}", status_code=204)
def unpublish(publication_id: str, d: DepsDep, user: User) -> Response:
    row = _need(d, publication_id)
    if row["author"] != user:
        raise HTTPException(403, f"only {row['author']} can unpublish {publication_id}")
    with d.engine.begin() as c:
        c.execute(delete(db.publications).where(db.publications.c.id == publication_id))
    return Response(status_code=204)


@router.post("/{publication_id}/fork", status_code=201)
async def fork(publication_id: str, body: ForkIn, d: DepsDep) -> ModelDetail:
    row = _need(d, publication_id)
    need_project(d, body.project_id)
    source = ForkSource(publication=publication_id, **{k: row[k] for k in ("model_id", "version", "title", "author")})
    model_id = await asyncio.to_thread(_copy, d, body.project_id, source)
    return detail(d, need_model(d, model_id))


def _copy(d: Deps, project_id: str, source: ForkSource) -> str:
    model_id = repo.create_model(d.engine, project_id, source.title)
    repo.set_model(d.engine, model_id, forked_from=source.model_dump())
    src = disk.version_dir(d.settings.data_dir, source.model_id, source.version)
    disk.copy_version(src, disk.version_dir(d.settings.data_dir, model_id, 1))
    data = repo.version(d.engine, source.model_id, source.version)
    assert data is not None
    prompt = f"forked from {source.title!r} v{source.version} by {source.author} ({source.publication})"
    forked = data.model_copy(
        update={"origin": "fork", "prompt": prompt, "created": repo.now(), "changes": None, "used": [], "inputs": [], "attachments": []}
    )
    repo.add_version(d.engine, model_id, 1, forked)
    with d.context_lock:
        d.context.record_generation(project_id, work.graph_id(model_id, 1), disk.design(src), [])
    return model_id


def _need(d: Deps, publication_id: str) -> Row:
    with d.engine.connect() as c:
        row = c.execute(select(db.publications).where(db.publications.c.id == publication_id)).first()
    if row is None:
        raise HTTPException(404, f"publication {publication_id} not found")
    return dict(row._mapping)


def _publication(d: Deps, row: Row) -> Publication:
    data = repo.version(d.engine, row["model_id"], row["version"])
    thumbnail = model_urls(row["model_id"], row["version"])("thumbnail") if data and data.thumbnail else None
    return Publication(**row, thumbnail_url=thumbnail)
