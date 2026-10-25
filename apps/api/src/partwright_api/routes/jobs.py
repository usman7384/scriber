from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette import EventSourceResponse

from partwright_api import jobs_db
from partwright_api.auth import require_token
from partwright_api.deps import DepsDep
from partwright_api.schemas import Job

router = APIRouter(prefix="/jobs/{job_id}", dependencies=[Depends(require_token)])


@router.get("")
def get_job(job_id: str, d: DepsDep) -> Job:
    job = jobs_db.get(d.engine, job_id)
    if job is None:
        raise HTTPException(404, f"job {job_id} not found")
    return job


@router.get("/events")
def events(job_id: str, request: Request, d: DepsDep) -> EventSourceResponse:
    get_job(job_id, d)
    last = request.headers.get("last-event-id", "")
    after = int(last) if last.isdigit() else -1

    async def stream() -> AsyncIterator[dict[str, str]]:
        async for kind, seq, payload in d.jobs.events(job_id, after):
            yield {"event": kind, "id": str(seq), "data": payload.model_dump_json()}

    return EventSourceResponse(stream())
