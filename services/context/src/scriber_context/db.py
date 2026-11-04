from sqlalchemy import JSON, Column, Integer, MetaData, String, Table, Text

metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("id", String, primary_key=True),
    Column("seq", Integer, nullable=False),
    Column("data", JSON, nullable=False),
)
chunks = Table(
    "chunks",
    metadata,
    Column("id", String, primary_key=True),
    Column("doc_id", String, nullable=False, index=True),
    Column("data", JSON, nullable=False),
)
facts = Table(
    "facts",
    metadata,
    Column("id", String, primary_key=True),
    Column("doc_id", String, nullable=False, index=True),
    Column("kind", String, nullable=False),
    Column("data", JSON, nullable=False),
)
rules = Table(
    "rules",
    metadata,
    Column("node_id", String, primary_key=True),
    Column("rule_id", String, nullable=False, index=True),
    Column("doc_id", String, index=True),
    Column("seq", Integer, nullable=False),
    Column("data", JSON, nullable=False),
)
nodes = Table(
    "nodes",
    metadata,
    Column("id", String, primary_key=True),
    Column("type", String, nullable=False, index=True),
    Column("name", String, nullable=False),
    Column("doc_id", String, index=True),
    Column("model_id", String, index=True),
    Column("props", JSON, nullable=False),
)
edges = Table(
    "edges",
    metadata,
    Column("src", String, primary_key=True),
    Column("dst", String, primary_key=True, index=True),
    Column("type", String, primary_key=True),
)
designs = Table(
    "designs",
    metadata,
    Column("model_id", String, primary_key=True),
    Column("data", JSON, nullable=False),
)
meta = Table(
    "meta",
    metadata,
    Column("key", String, primary_key=True),
    Column("value", Text, nullable=False),
)
