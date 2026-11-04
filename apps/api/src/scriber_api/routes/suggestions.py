import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import TypeAdapter

from scriber_agent import suggest
from scriber_api import disk, repo
from scriber_api.auth import require_token
from scriber_api.deps import Deps, DepsDep
from scriber_api.routes.common import latest_design, need_idle, need_model, need_ollama, start_rebuild
from scriber_api.schemas import FaceStress, Job, SimulationIn, SuggestionOut
from scriber_api.work import Rebuild, latest_ok
from scriber_geometry import Finding

router = APIRouter(prefix="/models/{model_id}/suggestions", dependencies=[Depends(require_token)])
simulation = APIRouter(prefix="/models/{model_id}", dependencies=[Depends(require_token)])
STORE = TypeAdapter(list[SuggestionOut])


@router.post("", status_code=201)
async def create(model_id: str, d: DepsDep) -> list[SuggestionOut]:
    need_model(d, model_id)
    return await _propose(d, model_id, latest_ok(d, model_id)[1].findings)


@simulation.post("/simulation", status_code=201)
async def simulated(model_id: str, body: SimulationIn, d: DepsDep) -> list[SuggestionOut]:
    need_model(d, model_id)
    groups = {g.name: p.id for p in latest_design(d, model_id).parts for g in p.face_groups}
    unknown = sorted({r.face_group for r in body.results} - set(groups))
    if unknown:
        raise HTTPException(400, f"unknown face groups {unknown}; the design names {sorted(groups)}")
    over = [_finding(body, r, groups[r.face_group]) for r in body.results if r.max_stress_mpa > r.allowable_mpa]
    return await _propose(d, model_id, over) if over else []


def _finding(sim: SimulationIn, r: FaceStress, part: str) -> Finding:
    ratio = r.max_stress_mpa / r.allowable_mpa
    case = " ".join(x for x in (sim.solver, sim.load_case) if x) or "simulation"
    message = (
        f"{case}: max stress {r.max_stress_mpa:g} MPa on face group {r.face_group} is {ratio:.2f}x the allowable {r.allowable_mpa:g} MPa"
    )
    return Finding(
        rule_id="simulation.stress",
        severity="error",
        message=message,
        part=part,
        measured=r.max_stress_mpa,
        required=r.allowable_mpa,
        suggestion=f"stiffen the section that carries the load into {r.face_group}",
    )


async def _propose(d: Deps, model_id: str, findings: list[Finding]) -> list[SuggestionOut]:
    need_idle(d, model_id)
    design = latest_design(d, model_id)
    await need_ollama(d)
    try:
        async with d.jobs.gpu:
            found = await asyncio.to_thread(suggest, design, findings, d.llm, d.settings.seed)
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
