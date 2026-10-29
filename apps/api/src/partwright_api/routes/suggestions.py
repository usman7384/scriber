import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter

from partwright_agent import suggest
from partwright_api import disk, repo
from partwright_api.auth import require_token
from partwright_api.deps import Deps, DepsDep
from partwright_api.routes.common import latest_design, need_idle, need_model, need_ollama, start_rebuild
from partwright_api.schemas import Job, SuggestionOut
from partwright_api.work import Rebuild, latest_ok

router = APIRouter(prefix="/models/{model_id}/suggestions", dependencies=[Depends(require_token)])
STORE = TypeAdapter(list[SuggestionOut])


@router.post("", status_code=201)
async def create(model_id: str, d: DepsDep) -> list[SuggestionOut]:
    need_model(d, model_id)
    need_idle(d, model_id)
    design = latest_design(d, model_id)
    _, data = latest_ok(d, model_id)
    await need_ollama(d)
    try:
        async with d.jobs.gpu:
            found = await asyncio.to_thread(suggest, design, data.findings, d.llm, d.settings.seed)
    except ValueError as e:
        raise HTTPException(502, f"could not make suggestions: {e}") from None
    made = [SuggestionOut(id=repo.new_id("g"), **s.model_dump()) for s in found]
    _save(d, model_id, made)
    return made


@router.get("")
def listing(model_id: str, d: DepsDep) -> list[SuggestionOut]:
    need_model(d, model_id)
    return _load(d, model_id)


@router.post("/{suggestion_id}/accept", status_code=202)
async def accept(model_id: str, suggestion_id: str, d: DepsDep) -> Job:
    model = need_model(d, model_id)
    s = _need(d, model_id, suggestion_id)
    job = start_rebuild(d, model, Rebuild(s.change, "suggestion", f"{s.target}: {s.rationale}"), "params")
    _mark(d, model_id, suggestion_id, "accepted")
    return job


@router.post("/{suggestion_id}/ignore")
def ignore(model_id: str, suggestion_id: str, d: DepsDep) -> SuggestionOut:
    need_model(d, model_id)
    _need(d, model_id, suggestion_id)
    return _mark(d, model_id, suggestion_id, "ignored")


def _need(d: Deps, model_id: str, suggestion_id: str) -> SuggestionOut:
    found = next((s for s in _load(d, model_id) if s.id == suggestion_id), None)
    if found is None:
        raise HTTPException(404, f"suggestion {suggestion_id} not found for model {model_id}")
    if found.status != "open":
        raise HTTPException(409, f"suggestion {suggestion_id} is already {found.status}")
    return found


def _mark(d: Deps, model_id: str, suggestion_id: str, status: str) -> SuggestionOut:
    items = [s.model_copy(update={"status": status}) if s.id == suggestion_id else s for s in _load(d, model_id)]
    _save(d, model_id, items)
    return next(s for s in items if s.id == suggestion_id)


def _load(d: Deps, model_id: str) -> list[SuggestionOut]:
    path = disk.suggestions_path(d.settings.data_dir, model_id)
    return STORE.validate_json(path.read_bytes()) if path.exists() else []


def _save(d: Deps, model_id: str, items: list[SuggestionOut]) -> None:
    path = disk.suggestions_path(d.settings.data_dir, model_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(STORE.dump_json(items, indent=2))
