import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, delete, func, insert, select, update

from partwright_api import db
from partwright_api.schemas import Project, VersionData

Row = dict[str, Any]


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return prefix + secrets.token_hex(6)


def create_project(e: Engine, name: str, project_id: str | None = None) -> Project:
    created = Project(id=project_id or new_id("p"), name=name, created=now(), model_count=0, file_count=0)
    with e.begin() as c:
        c.execute(insert(db.projects).values(id=created.id, name=name, created=created.created))
    return created


def project(e: Engine, project_id: str) -> Project | None:
    return next(iter(_projects(e, project_id)), None)


def projects(e: Engine) -> list[Project]:
    return _projects(e, None)


def _projects(e: Engine, project_id: str | None) -> list[Project]:
    models = select(func.count()).where(db.models.c.project_id == db.projects.c.id).scalar_subquery()
    files = select(func.count()).where(db.files.c.project_id == db.projects.c.id).scalar_subquery()
    query = select(db.projects, models.label("model_count"), files.label("file_count")).order_by(db.projects.c.created)
    if project_id is not None:
        query = query.where(db.projects.c.id == project_id)
    with e.connect() as c:
        return [Project.model_validate(dict(r._mapping)) for r in c.execute(query)]


def add_file(e: Engine, project_id: str, name: str) -> str:
    fid = new_id("f")
    with e.begin() as c:
        c.execute(insert(db.files).values(id=fid, project_id=project_id, name=name, status="processing", uploaded=now()))
    return fid


def set_file(e: Engine, file_id: str, **values: Any) -> None:
    with e.begin() as c:
        c.execute(update(db.files).where(db.files.c.id == file_id).values(**values))


def file_row(e: Engine, file_id: str) -> Row | None:
    return _one(e, select(db.files).where(db.files.c.id == file_id))


def file_rows(e: Engine, project_id: str) -> list[Row]:
    return _all(e, select(db.files).where(db.files.c.project_id == project_id).order_by(db.files.c.uploaded))


def delete_file(e: Engine, file_id: str) -> None:
    with e.begin() as c:
        c.execute(delete(db.files).where(db.files.c.id == file_id))


def create_model(e: Engine, project_id: str, title: str) -> str:
    mid = new_id("m")
    with e.begin() as c:
        c.execute(insert(db.models).values(id=mid, project_id=project_id, title=title[:60], created=now(), stale=False))
    return mid


def model_row(e: Engine, model_id: str) -> Row | None:
    return _one(e, select(db.models).where(db.models.c.id == model_id))


def model_rows(e: Engine, project_id: str) -> list[Row]:
    return _all(e, select(db.models).where(db.models.c.project_id == project_id).order_by(db.models.c.created))


def set_model(e: Engine, model_id: str, **values: Any) -> None:
    with e.begin() as c:
        c.execute(update(db.models).where(db.models.c.id == model_id).values(**values))


def mark_stale(e: Engine, model_ids: list[str]) -> None:
    with e.begin() as c:
        c.execute(update(db.models).where(db.models.c.id.in_(model_ids)).values(stale=True))


def add_version(e: Engine, model_id: str, number: int, data: VersionData) -> None:
    with e.begin() as c:
        c.execute(insert(db.versions).values(model_id=model_id, number=number, data=data.model_dump(mode="json")))


def version(e: Engine, model_id: str, number: int) -> VersionData | None:
    row = _one(e, select(db.versions).where(db.versions.c.model_id == model_id, db.versions.c.number == number))
    return VersionData.model_validate(row["data"]) if row else None


def versions(e: Engine, model_id: str) -> list[tuple[int, VersionData]]:
    rows = _all(e, select(db.versions).where(db.versions.c.model_id == model_id).order_by(db.versions.c.number))
    return [(r["number"], VersionData.model_validate(r["data"])) for r in rows]


def _one(e: Engine, query: Any) -> Row | None:
    with e.connect() as c:
        row = c.execute(query).first()
    return dict(row._mapping) if row else None


def _all(e: Engine, query: Any) -> list[Row]:
    with e.connect() as c:
        return [dict(r._mapping) for r in c.execute(query)]
