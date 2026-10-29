from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Boolean, Column, Engine, Integer, MetaData, String, Table, create_engine, event, inspect, text

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
    Column("forked_from", JSON),
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
    Column("request", JSON),
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

usage = Table(
    "usage",
    metadata,
    Column("id", String, primary_key=True),
    Column("user", String, nullable=False, index=True),
    Column("kind", String, nullable=False),
    Column("created", String, nullable=False),
)
bugs = Table(
    "bugs",
    metadata,
    Column("id", String, primary_key=True),
    Column("model_id", String, nullable=False, index=True),
    Column("version", Integer, nullable=False),
    Column("text", String, nullable=False),
    Column("user", String, nullable=False),
    Column("screenshot", Boolean, nullable=False),
    Column("created", String, nullable=False),
)
publications = Table(
    "publications",
    metadata,
    Column("id", String, primary_key=True),
    Column("model_id", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("title", String, nullable=False),
    Column("author", String, nullable=False),
    Column("created", String, nullable=False),
)


# The only SQLite-specific code in the API: the URL and WAL mode.
def open_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}")
    event.listen(engine, "connect", _wal)
    metadata.create_all(engine)
    _add_missing_columns(engine)
    return engine


def _add_missing_columns(engine: Engine) -> None:
    existing = {t: {c["name"] for c in inspect(engine).get_columns(t)} for t in metadata.tables}
    with engine.begin() as c:
        for table in metadata.sorted_tables:
            for column in table.columns:
                if column.name not in existing[table.name]:
                    kind = column.type.compile(engine.dialect)
                    c.execute(text(f"alter table {table.name} add column {column.name} {kind}"))


def _wal(dbapi_connection: Any, _record: Any) -> None:
    dbapi_connection.execute("pragma journal_mode=wal")
