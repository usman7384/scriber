from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from scriber_api import access, repo, tools, views
from scriber_api.auth import User, require_token, require_token_unless_first
from scriber_api.deps import Deps, DepsDep
from scriber_api.disk import FILE_NAMES
from scriber_api.repo import Row
from scriber_api.routes.common import export, need_model, need_version, ollama_up
from scriber_api.routes.models import thumbnail_file
from scriber_api.schemas import FileKind, Health, Hook, HookIn, ModelDetail, NewToken, Share, ShareIn, Token, TokenIn, Usage

router = APIRouter(dependencies=[Depends(require_token)])
tokens = APIRouter(dependencies=[Depends(require_token_unless_first)])
public = APIRouter()


@router.post("/shares", status_code=201)
def create_share(body: ShareIn, d: DepsDep) -> Share:
    need_model(d, body.model_id)
    if body.version is not None:
        need_version(d, body.model_id, body.version)
    share_id = access.create_share(d.engine, body.model_id, body.version)
    return Share(id=share_id, url=f"/s/{share_id}")


@router.delete("/shares/{share_id}", status_code=204)
def delete_share(share_id: str, d: DepsDep) -> Response:
    return _deleted(access.remove(d.engine, "shares", share_id), "share", share_id)


@router.get("/usage")
def usage(d: DepsDep, user: User) -> Usage:
    return Usage(user=user, generations=access.generations(d.engine, user), limit=d.settings.generation_limit)


@router.post("/hooks", status_code=201)
def create_hook(body: HookIn, d: DepsDep) -> Hook:
    return access.create_hook(d.engine, body.url, body.events)


@router.delete("/hooks/{hook_id}", status_code=204)
def delete_hook(hook_id: str, d: DepsDep) -> Response:
    return _deleted(access.remove(d.engine, "hooks", hook_id), "hook", hook_id)


@tokens.post("/tokens", status_code=201)
def create_token(body: TokenIn, d: DepsDep) -> NewToken:
    return access.create_token(d.engine, body.name)


@tokens.get("/tokens")
def list_tokens(d: DepsDep) -> list[Token]:
    return access.tokens(d.engine)


@tokens.delete("/tokens/{token_id}", status_code=204)
def delete_token(token_id: str, d: DepsDep) -> Response:
    return _deleted(access.remove(d.engine, "tokens", token_id), "token", token_id)


@public.get("/health")
async def health(d: DepsDep) -> Health:
    return Health(status="ok", model=d.llm.name, ollama=await ollama_up(d), tools=tools.available(d))


@public.get("/s/{share_id}")
def shared(share_id: str, d: DepsDep) -> ModelDetail:
    row, model = _share(d, share_id)
    n, data = need_version(d, model["id"], row["version"])
    version = views.version(model["id"], n, data, views.share_urls(share_id))
    summary = views.model(model, repo.versions(d.engine, model["id"])).model_dump()
    return ModelDetail(**{**summary, "thumbnail_url": version.thumbnail_url}, version=version)


@public.get("/s/{share_id}/files/{kind}")
def shared_file(share_id: str, kind: str, d: DepsDep) -> FileResponse:
    row, model = _share(d, share_id)
    number = need_version(d, model["id"], row["version"])[0]
    if kind == "thumbnail":
        return thumbnail_file(d, model["id"], number)
    if kind not in FILE_NAMES:
        raise HTTPException(404, f"unknown file {kind!r}")
    return export(d, model, cast(FileKind, kind), number)


def _share(d: Deps, share_id: str) -> tuple[Row, Row]:
    row = access.share(d.engine, share_id)
    if row is None:
        raise HTTPException(404, "share link not found or revoked")
    return row, need_model(d, row["model_id"])


def _deleted(found: bool, what: str, item_id: str) -> Response:
    if not found:
        raise HTTPException(404, f"{what} {item_id} not found")
    return Response(status_code=204)
