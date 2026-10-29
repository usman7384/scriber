import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from typing import Any

import structlog
from pydantic import JsonValue
from sqlalchemy import Engine
from structlog.contextvars import bound_contextvars

from partwright_api import jobs_db
from partwright_api.hooks import Hooks
from partwright_api.schemas import HookEvent, Job, JobKind, Step

log = structlog.get_logger()
GPU_KINDS = frozenset({"generate", "refine", "edit"})
Emit = Callable[[Step], None]
Event = tuple[str, int, Step | Job]


@dataclass(frozen=True)
class Outcome:
    version: int | None = None
    error: str | None = None
    events: tuple[tuple[HookEvent, dict[str, Any]], ...] = ()
    followups: tuple[Callable[[], object], ...] = ()


Work = Callable[[Emit], Outcome]


class Jobs:
    def __init__(self, engine: Engine, hooks: Hooks) -> None:
        self._engine = engine
        self._hooks = hooks
        self.gpu = asyncio.Semaphore(1)
        self._queues: dict[str, list[asyncio.Queue[Event]]] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        if interrupted := jobs_db.interrupt(engine):
            log.warning("jobs_interrupted", count=interrupted)

    def submit(self, kind: JobKind, project_id: str, model_id: str | None, work: Work, request: dict[str, JsonValue] | None = None) -> Job:
        job = jobs_db.create(self._engine, kind, project_id, model_id, request)
        task = asyncio.get_running_loop().create_task(self._run(job.id, kind, work))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    async def drain(self) -> None:
        await asyncio.gather(*self._tasks)

    async def events(self, job_id: str, after: int = -1) -> AsyncIterator[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._queues.setdefault(job_id, []).append(queue)
        try:
            job = jobs_db.get(self._engine, job_id)
            assert job is not None
            for seq, step in enumerate(job.steps):
                if seq > after:
                    yield "step", seq, step
            after = max(after, len(job.steps) - 1)
            if job.status in ("done", "failed"):
                yield job.status, len(job.steps), job
                return
            while True:
                kind, seq, payload = await queue.get()
                if kind != "step":
                    yield kind, seq, payload
                    return
                if seq > after:
                    after = seq
                    yield kind, seq, payload
        finally:
            self._queues[job_id].remove(queue)
            if not self._queues[job_id]:
                del self._queues[job_id]

    async def _run(self, job_id: str, kind: JobKind, work: Work) -> None:
        with bound_contextvars(job_id=job_id):
            if kind in GPU_KINDS:
                async with self.gpu:
                    await self._execute(job_id, work)
            else:
                await self._execute(job_id, work)

    async def _execute(self, job_id: str, work: Work) -> None:
        loop = asyncio.get_running_loop()
        jobs_db.start(self._engine, job_id)
        log.info("job_started")

        def emit(step: Step) -> None:
            seq = jobs_db.add_step(self._engine, job_id, step)
            loop.call_soon_threadsafe(self._publish, job_id, ("step", seq, step))

        try:
            outcome = await asyncio.to_thread(work, emit)
        except Exception as e:
            log.exception("job_crashed")
            outcome = Outcome(error=f"{type(e).__name__}: {e}")
        jobs_db.finish(self._engine, job_id, outcome.error, version=outcome.version)
        job = jobs_db.get(self._engine, job_id)
        assert job is not None
        self._publish(job_id, (job.status, len(job.steps), job))
        log.info("job_finished", status=job.status, error=job.error, version=job.version)
        for event, payload in outcome.events:
            self._hooks.fire(event, payload)
        if job.status == "failed":
            self._hooks.fire("job.failed", {"job": job.model_dump(mode="json")})
        for followup in outcome.followups:
            try:
                followup()
            except Exception:
                log.exception("followup_failed")

    def _publish(self, job_id: str, event: Event) -> None:
        for queue in self._queues.get(job_id, []):
            queue.put_nowait(event)
