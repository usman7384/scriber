import base64
import binascii
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import insert, select

from partwright_api import db, repo
from partwright_api.auth import User, require_token
from partwright_api.deps import Deps, DepsDep
from partwright_api.routes.common import need_model, need_version
from partwright_api.schemas import Bug, BugIn

router = APIRouter(prefix="/bugs", dependencies=[Depends(require_token)])
DATA_URL = re.compile(r"^data:image/(png|jpeg);base64,(.+)$", re.DOTALL)
MAGIC = {"png": b"\x89PNG\r\n\x1a\n", "jpeg": b"\xff\xd8\xff"}


@router.post("", status_code=201)
def report(body: BugIn, d: DepsDep, user: User) -> Bug:
    need_model(d, body.model_id)
    need_version(d, body.model_id, body.version)
    image = _image(body.screenshot) if body.screenshot else None
    bug_id = repo.new_id("b")
    if image:
        path = _screenshot(d, bug_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image)
    row = {**body.model_dump(exclude={"screenshot"}), "id": bug_id, "user": user, "screenshot": image is not None, "created": repo.now()}
    with d.engine.begin() as c:
        c.execute(insert(db.bugs).values(**row))
    return _bug(row)


@router.get("")
def listing(d: DepsDep, model_id: str | None = None) -> list[Bug]:
    query = select(db.bugs).order_by(db.bugs.c.created)
    if model_id is not None:
        query = query.where(db.bugs.c.model_id == model_id)
    with d.engine.connect() as c:
        return [_bug(dict(r._mapping)) for r in c.execute(query)]


@router.get("/{bug_id}/screenshot")
def screenshot(bug_id: str, d: DepsDep) -> FileResponse:
    path = _screenshot(d, bug_id)
    if not path.exists():
        raise HTTPException(404, f"bug {bug_id} has no screenshot")
    media = "image/png" if path.read_bytes().startswith(MAGIC["png"]) else "image/jpeg"
    return FileResponse(path, media_type=media)


def _image(data_url: str) -> bytes:
    match = DATA_URL.match(data_url)
    if not match:
        raise HTTPException(422, "screenshot must be a data:image/png or data:image/jpeg base64 URL")
    try:
        image = base64.b64decode(match.group(2), validate=True)
    except binascii.Error:
        raise HTTPException(422, "screenshot is not valid base64") from None
    if not image.startswith(MAGIC[match.group(1)]):
        raise HTTPException(422, f"screenshot is not a {match.group(1).upper()} image")
    return image


def _screenshot(d: Deps, bug_id: str) -> Path:
    return d.settings.data_dir / "bugs" / f"{bug_id}.img"


def _bug(row: dict[str, object]) -> Bug:
    url = f"/bugs/{row['id']}/screenshot" if row["screenshot"] else None
    return Bug.model_validate({**row, "screenshot_url": url})
