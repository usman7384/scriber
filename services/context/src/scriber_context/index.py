import re
import struct
from pathlib import Path
from typing import Any

import sqlite_vec
from sqlalchemy import Connection, Engine, create_engine, event

from scriber_context.db import metadata

# The only SQLite-specific module: FTS5 keyword index, sqlite-vec vectors and the engine that loads the extension.


def open_engine(path: Path, dim: int) -> Engine:
    engine = create_engine(f"sqlite:///{path}")
    event.listen(engine, "connect", _load_vec)
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("create virtual table if not exists chunk_text using fts5(chunk_id unindexed, text)")
        conn.exec_driver_sql(f"create virtual table if not exists chunk_vec using vec0(chunk_id text primary key, embedding float[{dim}])")
        conn.exec_driver_sql(f"create virtual table if not exists part_vec using vec0(part_id text primary key, embedding float[{dim}])")
    return engine


def _load_vec(dbapi_connection: Any, _record: Any) -> None:
    dbapi_connection.enable_load_extension(True)
    sqlite_vec.load(dbapi_connection)
    dbapi_connection.enable_load_extension(False)


def add_chunks(conn: Connection, items: list[tuple[str, str, list[float]]]) -> None:
    if items:
        conn.exec_driver_sql("insert into chunk_text(chunk_id, text) values (?, ?)", [(i, t) for i, t, _ in items])
        conn.exec_driver_sql(
            "insert into chunk_vec(chunk_id, embedding) values (?, ?)", [(i, sqlite_vec.serialize_float32(v)) for i, _, v in items]
        )


def add_part(conn: Connection, part_id: str, vector: list[float]) -> None:
    conn.exec_driver_sql("delete from part_vec where part_id = ?", (part_id,))
    conn.exec_driver_sql("insert into part_vec(part_id, embedding) values (?, ?)", (part_id, sqlite_vec.serialize_float32(vector)))


def remove(conn: Connection, chunk_ids: list[str], part_ids: list[str]) -> None:
    for i in chunk_ids:
        conn.exec_driver_sql("delete from chunk_text where chunk_id = ?", (i,))
        conn.exec_driver_sql("delete from chunk_vec where chunk_id = ?", (i,))
    for i in part_ids:
        conn.exec_driver_sql("delete from part_vec where part_id = ?", (i,))


def keyword(conn: Connection, query: str, k: int) -> list[str]:
    tokens = re.findall(r"\w+", query)
    if not tokens:
        return []
    match = " OR ".join(f'"{t}"' for t in tokens)
    rows = conn.exec_driver_sql("select chunk_id from chunk_text where chunk_text match ? order by rank limit ?", (match, k))
    return [r[0] for r in rows]


def nearest(conn: Connection, vector: list[float], k: int) -> list[str]:
    rows = conn.exec_driver_sql(
        "select chunk_id from chunk_vec where embedding match ? and k = ? order by distance", (sqlite_vec.serialize_float32(vector), k)
    )
    return [r[0] for r in rows]


def part_vectors(conn: Connection) -> dict[str, list[float]]:
    rows = conn.exec_driver_sql("select part_id, embedding from part_vec")
    return {r[0]: list(struct.unpack(f"{len(r[1]) // 4}f", r[1])) for r in rows}
