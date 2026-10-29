from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from partwright_agent import LLM
from partwright_api import db, logs
from partwright_api.deps import Deps, Geometry, SerialGeometry
from partwright_api.hooks import Hooks
from partwright_api.jobs import Jobs
from partwright_api.routes import context, jobs, models, projects, sharing, suggestions, v1
from partwright_api.settings import Settings
from partwright_context import Context


def create_app(
    settings: Settings,
    llm: LLM,
    geometry: Geometry,
    context_service: Context,
    transport: httpx.AsyncBaseTransport | None = None,
    vision: LLM | None = None,
) -> FastAPI:
    logs.setup()
    engine = db.open_engine(settings.data_dir / "api.sqlite")
    http = httpx.AsyncClient(transport=transport)
    hooks = Hooks(engine, http, settings)
    serial = geometry if isinstance(geometry, SerialGeometry) else SerialGeometry(geometry)
    deps = Deps(settings, engine, llm, serial, context_service, http, hooks, Jobs(engine, hooks), vision)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await hooks.drain()
        await http.aclose()
        engine.dispose()

    app = FastAPI(title="Partwright API", version="0.1.0", lifespan=lifespan)
    app.state.deps = deps
    app.add_middleware(logs.RequestContext)
    routers = (projects.router, context.router, models.router, suggestions.router, jobs.router, v1.router)
    for router in (*routers, sharing.router, sharing.tokens, sharing.public):
        app.include_router(router)
    return app
