import sys
import time

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from structlog.contextvars import bound_contextvars

from partwright_api.repo import new_id

log = structlog.get_logger()


def setup() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
    )


class RequestContext:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = dict(scope["headers"]).get(b"x-request-id", b"").decode() or new_id("r")
        status = 500
        start = time.monotonic()

        async def tagged(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = [*message.get("headers", []), (b"x-request-id", request_id.encode())]
            await send(message)

        with bound_contextvars(request_id=request_id):
            try:
                await self.app(scope, receive, tagged)
            finally:
                ms = int((time.monotonic() - start) * 1000)
                log.info("request", method=scope["method"], path=scope["path"], status=status, ms=ms)
