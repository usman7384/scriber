from fastapi import HTTPException, Request

from partwright_api import access
from partwright_api.deps import deps


def require_token(request: Request) -> None:
    d = deps(request)
    if d.settings.auth == "none":
        return
    bearer = request.headers.get("authorization", "")
    token = bearer.removeprefix("Bearer ").strip() if bearer.startswith("Bearer ") else request.headers.get("x-api-token", "")
    if not token or not access.valid_token(d.engine, token):
        raise HTTPException(401, "missing or invalid API token")


def require_token_unless_first(request: Request) -> None:
    d = deps(request)
    if request.method == "POST" and not access.tokens(d.engine):
        return
    require_token(request)
