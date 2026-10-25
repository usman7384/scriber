import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from partwright_api import repo
from partwright_api.deps import Deps
from partwright_api.jobs import Emit, Outcome
from partwright_api.repo import Row
from partwright_api.schemas import HookEvent, Step
from partwright_context import Fact

Events = list[tuple[HookEvent, dict[str, Any]]]


def ingest(d: Deps, project_id: str, file_id: str, path: Path, emit: Emit) -> Outcome:
    start = time.monotonic()
    try:
        with d.context_lock:
            doc = d.context.ingest(project_id, path)
    except Exception as e:
        repo.set_file(d.engine, file_id, status="failed", error=f"{type(e).__name__}: {e}")
        raise
    repo.set_file(d.engine, file_id, status="processed", doc_id=doc.id)
    message = f"{doc.name}: {doc.kind}, {doc.chunks} chunks, {doc.facts} facts, {doc.rules} rules"
    emit(Step(kind="ingest", message=message, attempt=1, elapsed_ms=int((time.monotonic() - start) * 1000)))
    events: Events = []
    for old in repo.file_rows(d.engine, project_id):
        if old["name"] == path.name and old["id"] != file_id and old["status"] != "processing":
            events += replace(d, project_id, old, doc.id)
    return Outcome(events=tuple(events))


def replace(d: Deps, project_id: str, old: Row, new_doc: str) -> Events:
    if old["doc_id"] is None or old["doc_id"] == new_doc:
        drop(d, project_id, old["id"])
        return []
    with d.context_lock:
        before, after = d.context.facts(project_id, old["doc_id"]), d.context.facts(project_id, new_doc)
    return remove(d, project_id, old, changed(before, after))


def remove(d: Deps, project_id: str, row: Row, changed_facts: list[str] | None = None) -> Events:
    ids: list[str] = []
    stale: list[str] = []
    shared = any(r["doc_id"] == row["doc_id"] and r["id"] != row["id"] for r in repo.file_rows(d.engine, project_id))
    if row["doc_id"] is not None and not shared:
        with d.context_lock:
            ids = changed_facts if changed_facts is not None else [f.id for f in d.context.facts(project_id, row["doc_id"])]
            stale = d.context.stale(project_id, ids)
            d.context.delete_document(project_id, row["doc_id"])
    drop(d, project_id, row["id"])
    versions: dict[str, list[int]] = defaultdict(list)
    for graph_id in stale:
        model_id, number = graph_id.rsplit("/v", 1)
        versions[model_id].append(int(number))
    repo.mark_stale(d.engine, list(versions))
    payload = {"project_id": project_id, "file_id": row["id"], "changed_facts": ids}
    return [("version.stale", {**payload, "model_id": m, "versions": sorted(v)}) for m, v in versions.items()]


def drop(d: Deps, project_id: str, file_id: str) -> None:
    repo.delete_file(d.engine, file_id)
    folder = d.settings.data_dir / "uploads" / project_id / file_id
    if folder.exists():
        shutil.rmtree(folder)


def changed(before: list[Fact], after: list[Fact]) -> list[str]:
    kept = {_key(f) for f in after}
    return [f.id for f in before if _key(f) not in kept]


def _key(f: Fact) -> tuple[object, ...]:
    return f.name, f.value, f.unit, f.tol, f.count
