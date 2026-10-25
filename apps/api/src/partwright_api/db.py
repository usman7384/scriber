from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Boolean, Column, Engine, Integer, MetaData, String, Table, create_engine, event

metadata = MetaData()

projects = Table(
    "projects", metadata, Column("id", String, primary_key=True), Column("name", String, nullable=False), Column("created", String)
)
files = Table(
    "files",
    metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False, index=True),
    Column("name", String, nullable=False),
    Column("status", String, nullable=False),
    Column("error", String),
    Column("doc_id", String),
    Column("uploaded", String, nullable=False),
)
models = Table(
    "models",
    metadata,
    Column("id", String, primary_key=True),
    Column("project_id", String, nullable=False, index=True),
    Column("title", String, nullable=False),
    Column("created", String, nullable=False),
    Column("stale", Boolean, nullable=False, default=False),
)
versions = Table(
    "versions",
    metadata,
    Column("model_id", String, primary_key=True),
    Column("number", Integer, primary_key=True),
    Column("data", JSON, nullable=False),
)
jobs = Table(
    "jobs",
    metadata,
    Column("id", String, primary_key=True),
    Column("kind", String, nullable=False),
    Column("status", String, nullable=False, index=True),
    Column("project_id", String, nullable=False),
    Column("model_id", String, index=True),
    Column("version", Integer),
    Column("error", String),
    Column("created", String, nullable=False),
    Column("started", String),
    Column("finished", String),
)
job_steps = Table(
    "job_steps",
    metadata,
    Column("job_id", String, primary_key=True),
    Column("seq", Integer, primary_key=True),
    Column("data", JSON, nullable=False),
)
tokens = Table(
    "tokens",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("digest", String, nullable=False, unique=True),
    Column("created", String, nullable=False),
)
shares = Table(
    "shares",
    metadata,
    Column("id", String, primary_key=True),
    Column("model_id", String, nullable=False),
    Column("version", Integer),
    Column("created", String, nullable=False),
)
hooks = Table(
    "hooks",
    metadata,
    Column("id", String, primary_key=True),
    Column("url", String, nullable=False),
    Column("events", JSON, nullable=False),
    Column("created", String, nullable=False),
)


# The only SQLite-specific code in the API: the URL and WAL mode.
def open_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    event.listen(engine, "connect", _wal)
    metadata.create_all(engine)
    return engine


def _wal(dbapi_connection: Any, _record: Any) -> None:
    dbapi_connection.execute("pragma journal_mode=wal")
