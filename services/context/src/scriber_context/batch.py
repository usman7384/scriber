from pathlib import Path
from typing import Literal

from scriber_context.models import FileKind, Frozen
from scriber_context.protocol import Context


class IngestOutcome(Frozen):
    name: str
    status: Literal["parsed", "failed"]
    kind: FileKind | None = None
    facts: int = 0
    error: str | None = None


def archive_files(paths: list[Path]) -> list[Path]:
    return [f for p in paths for f in (sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p])]


def ingest_all(context: Context, project_id: str, paths: list[Path]) -> list[IngestOutcome]:
    return [_ingest(context, project_id, p) for p in paths]


def _ingest(context: Context, project_id: str, path: Path) -> IngestOutcome:
    try:
        doc = context.ingest(project_id, path)
    except Exception as e:  # a bad file must not stop the archive; its error goes into the report
        return IngestOutcome(name=path.name, status="failed", error=f"{type(e).__name__}: {e}"[:500])
    return IngestOutcome(name=path.name, status="parsed", kind=doc.kind, facts=doc.facts)
