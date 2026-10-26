from typing import Any

from pydantic import JsonValue
from sqlalchemy import Engine, func, insert, select, update

from partwright_api import db
from partwright_api.repo import new_id, now
from partwright_api.schemas import Job, JobKind, Step

ACTIVE = ("queued", "running")


def create(e: Engine, kind: JobKind, project_id: str, model_id: str | None, request: dict[str, JsonValue] | None = None) -> Job:
    job = Job(id=new_id("j"), kind=kind, status="queued", project_id=project_id, model_id=model_id, created=now(), request=request)
    with e.begin() as c:
        c.execute(insert(db.jobs).values(**job.model_dump(exclude={"steps"})))
    return job


def start(e: Engine, job_id: str) -> None:
    _set(e, job_id, status="running", started=now())


def finish(e: Engine, job_id: str, error: str | None, **values: Any) -> None:
    _set(e, job_id, status="failed" if error else "done", error=error, finished=now(), **values)


def add_step(e: Engine, job_id: str, step: Step) -> int:
    with e.begin() as c:
        seq = c.execute(select(func.count()).where(db.job_steps.c.job_id == job_id)).scalar_one()
        c.execute(insert(db.job_steps).values(job_id=job_id, seq=seq, data=step.model_dump(mode="json")))
    return int(seq)


def get(e: Engine, job_id: str) -> Job | None:
    with e.connect() as c:
        row = c.execute(select(db.jobs).where(db.jobs.c.id == job_id)).first()
        if row is None:
            return None
        steps = c.execute(select(db.job_steps.c.data).where(db.job_steps.c.job_id == job_id).order_by(db.job_steps.c.seq)).scalars()
        return Job.model_validate({**row._mapping, "steps": list(steps)})


def for_project(e: Engine, project_id: str, active_only: bool) -> list[Job]:
    query = select(db.jobs.c.id).where(db.jobs.c.project_id == project_id).order_by(db.jobs.c.created.desc())
    if active_only:
        query = query.where(db.jobs.c.status.in_(ACTIVE))
    with e.connect() as c:
        ids = list(c.execute(query).scalars())
    return [job for job in (get(e, i) for i in ids) if job is not None]


def busy(e: Engine, model_id: str) -> bool:
    with e.connect() as c:
        return c.execute(select(db.jobs.c.id).where(db.jobs.c.model_id == model_id, db.jobs.c.status.in_(ACTIVE))).first() is not None


def interrupt(e: Engine) -> int:
    with e.begin() as c:
        result = c.execute(update(db.jobs).where(db.jobs.c.status.in_(ACTIVE)).values(status="failed", error="interrupted", finished=now()))
    return int(result.rowcount)


def _set(e: Engine, job_id: str, **values: Any) -> None:
    with e.begin() as c:
        c.execute(update(db.jobs).where(db.jobs.c.id == job_id).values(**values))
