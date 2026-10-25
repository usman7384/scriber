import asyncio
from typing import Any

import httpx
import structlog
from sqlalchemy import Engine

from partwright_api import access
from partwright_api.schemas import Hook, HookEvent
from partwright_api.settings import Settings

log = structlog.get_logger()
Payload = dict[str, Any]


class Hooks:
    def __init__(self, engine: Engine, http: httpx.AsyncClient, settings: Settings) -> None:
        self._engine = engine
        self._http = http
        self._settings = settings
        self._tasks: set[asyncio.Task[None]] = set()

    def fire(self, event: HookEvent, payload: Payload) -> None:
        for hook in access.hooks_for(self._engine, event):
            task = asyncio.get_running_loop().create_task(self._deliver(hook, {"event": event, **payload}))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        await asyncio.gather(*self._tasks)

    async def _deliver(self, hook: Hook, body: Payload) -> None:
        attempts, backoff = self._settings.hook_attempts, self._settings.hook_backoff_s
        for attempt in range(1, attempts + 1):
            try:
                response = await self._http.post(hook.url, json=body, timeout=10)
            except httpx.TransportError as e:
                log.warning("hook_unreachable", hook_id=hook.id, attempt=attempt, error=str(e))
            else:
                if response.status_code < 500:
                    log.info("hook_delivered", hook_id=hook.id, hook_event=body["event"], status=response.status_code, attempt=attempt)
                    return
                log.warning("hook_server_error", hook_id=hook.id, attempt=attempt, status=response.status_code)
            if attempt < attempts:
                await asyncio.sleep(backoff * 2 ** (attempt - 1))
        log.error("hook_gave_up", hook_id=hook.id, hook_event=body["event"], attempts=attempts)
