from collections.abc import Callable
from dataclasses import asdict

from scriber_api import schemas
from scriber_api.disk import FILE_NAMES
from scriber_api.repo import Row
from scriber_api.schemas import ForkSource, MaterialOut, Model, Version, VersionData
from scriber_context import Document
from scriber_context import Fact as ContextFact
from scriber_ir import Material, Rule

Urls = Callable[[str], str]


def model_urls(model_id: str, number: int) -> Urls:
    def url(kind: str) -> str:
        if kind == "thumbnail":
            return f"/models/{model_id}/versions/{number}/thumbnail"
        return f"/models/{model_id}/export?fmt={kind}&version={number}"

    return url


def share_urls(share_id: str) -> Urls:
    return lambda kind: f"/s/{share_id}/files/{kind}"


def version(model_id: str, number: int, data: VersionData, urls: Urls) -> Version:
    return Version(
        model_id=model_id,
        number=number,
        created=data.created,
        status=data.status,
        origin=data.origin,
        prompt=data.prompt,
        params=data.params,
        checks=data.checks,
        findings=data.findings,
        metrics=data.metrics,
        files={k: urls(k) for k in FILE_NAMES} if data.metrics else {},
        thumbnail_url=urls("thumbnail") if data.thumbnail else None,
        attachments=data.attachments,
        inputs=data.inputs,
        changes=data.changes,
    )


def model(row: Row, versions: list[tuple[int, VersionData]]) -> Model:
    latest = versions[-1] if versions else None
    thumbnail = next((model_urls(row["id"], n)("thumbnail") for n, v in reversed(versions) if v.thumbnail), None)
    return Model(
        id=row["id"],
        project_id=row["project_id"],
        title=row["title"],
        created=row["created"],
        latest_version=latest[0] if latest else None,
        versions=len(versions),
        thumbnail_url=thumbnail,
        stale=row["stale"],
        forked_from=ForkSource.model_validate(row["forked_from"]) if row.get("forked_from") else None,
    )


def file(row: Row, doc: Document | None, used_in: list[str]) -> schemas.File:
    counts = {"kind": doc.kind, "role": doc.role, "facts": doc.facts, "rules": doc.rules} if doc else {"kind": None, "role": None}
    keys = ("id", "project_id", "name", "status", "error", "uploaded")
    return schemas.File.model_validate({**{k: row[k] for k in keys}, **counts, "used_in": used_in})


def fact(f: ContextFact, file_id: str) -> schemas.Fact:
    return schemas.Fact(
        id=f.id,
        file_id=file_id,
        kind=f.kind,
        name=f.name,
        value=f.value,
        unit=f.unit,
        tol=f.tol,
        count=f.count,
        page=f.page,
        line=f.line,
        text=f.text,
        ref=f.source.ref,
    )


def rule(r: Rule) -> schemas.Rule:
    return schemas.Rule.model_validate({**r.model_dump(exclude={"source"}), "source_ref": r.source.ref})


def material(m: Material) -> MaterialOut:
    return MaterialOut(**asdict(m))
