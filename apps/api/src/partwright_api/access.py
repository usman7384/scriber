import hashlib
import secrets

from sqlalchemy import Engine, delete, func, insert, select

from partwright_api import db
from partwright_api.repo import Row, new_id, now
from partwright_api.schemas import Hook, HookEvent, NewToken, Token


def create_token(e: Engine, name: str) -> NewToken:
    token = NewToken(id=new_id("t"), name=name, created=now(), token="pw_" + secrets.token_urlsafe(24))
    with e.begin() as c:
        c.execute(insert(db.tokens).values(id=token.id, name=name, digest=_digest(token.token), created=token.created))
    return token


def tokens(e: Engine) -> list[Token]:
    with e.connect() as c:
        rows = c.execute(select(db.tokens.c.id, db.tokens.c.name, db.tokens.c.created).order_by(db.tokens.c.created))
        return [Token.model_validate(dict(r._mapping)) for r in rows]


def token_user(e: Engine, token: str) -> str | None:
    with e.connect() as c:
        name = c.execute(select(db.tokens.c.name).where(db.tokens.c.digest == _digest(token))).scalar()
    return None if name is None else str(name)


def charge(e: Engine, user: str, kind: str, count: int, limit: int | None) -> bool:
    with e.begin() as c:
        used = c.execute(select(func.count()).where(db.usage.c.user == user)).scalar_one()
        if limit is not None and used + count > limit:
            return False
        c.execute(insert(db.usage), [{"id": new_id("u"), "user": user, "kind": kind, "created": now()} for _ in range(count)])
    return True


def generations(e: Engine, user: str) -> int:
    with e.connect() as c:
        return int(c.execute(select(func.count()).where(db.usage.c.user == user)).scalar_one())


def create_share(e: Engine, model_id: str, version: int | None) -> str:
    sid = "s" + secrets.token_urlsafe(12)
    with e.begin() as c:
        c.execute(insert(db.shares).values(id=sid, model_id=model_id, version=version, created=now()))
    return sid


def share(e: Engine, share_id: str) -> Row | None:
    with e.connect() as c:
        row = c.execute(select(db.shares).where(db.shares.c.id == share_id)).first()
    return dict(row._mapping) if row else None


def create_hook(e: Engine, url: str, events: list[HookEvent]) -> Hook:
    hook = Hook(id=new_id("h"), url=url, events=events)
    with e.begin() as c:
        c.execute(insert(db.hooks).values(**hook.model_dump(), created=now()))
    return hook


def hooks_for(e: Engine, event: HookEvent) -> list[Hook]:
    with e.connect() as c:
        rows = [Hook.model_validate(dict(r._mapping)) for r in c.execute(select(db.hooks.c.id, db.hooks.c.url, db.hooks.c.events))]
    return [h for h in rows if event in h.events]


def remove(e: Engine, table: str, row_id: str) -> bool:
    t = db.metadata.tables[table]
    with e.begin() as c:
        return bool(c.execute(delete(t).where(t.c.id == row_id)).rowcount)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
