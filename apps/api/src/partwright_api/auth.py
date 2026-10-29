from typing import Annotated

from fastapi import Depends, HTTPException, Request

from partwright_api import access
from partwright_api.deps import deps

LOCAL_USER = "local"


def require_token(request: Request) -> None:
    current_user(request)


def require_token_unless_first(request: Request) -> None:
    d = deps(request)
    if request.method == "POST" and not access.tokens(d.engine):
        return
    require_token(request)


def current_user(request: Request) -> str:
    d = deps(request)
    if d.settings.auth == "none":
        return LOCAL_USER
    bearer = request.headers.get("authorization", "")
    token = bearer.removeprefix("Bearer ").strip() if bearer.startswith("Bearer ") else request.headers.get("x-api-token", "")
    user = access.token_user(d.engine, token) if token else None
    if user is None:
        raise HTTPException(401, "missing or invalid API token")
    return user


User = Annotated[str, Depends(current_user)]
