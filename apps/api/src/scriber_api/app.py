from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from scriber_agent import LLM
from scriber_api import db, logs
from scriber_api.deps import Deps, Geometry, SerialGeometry
from scriber_api.hooks import Hooks
from scriber_api.jobs import Jobs
from scriber_api.routes import bugs, community, context, designs, faces, jobs, materials, models, projects, sharing, suggestions, v1
from scriber_api.settings import Settings
from scriber_context import Context


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

    app = FastAPI(title="Scriber API", version="0.1.0", lifespan=lifespan)
    app.state.deps = deps
    app.add_middleware(logs.RequestContext)
    routers = (
        *(projects.router, designs.router, context.router, models.router, faces.router, suggestions.router, suggestions.simulation),
        *(jobs.router, v1.router, materials.router, bugs.router, community.router, sharing.router, sharing.tokens, sharing.public),
    )
    for router in routers:
        app.include_router(router)
    return app
