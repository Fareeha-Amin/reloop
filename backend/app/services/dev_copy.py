"""Copy the development database's rows into the test database, for demonstrations.

Dev is only ever READ: the source connection is opened read-only, so the database itself
refuses a write on it. The target must be the test database and must be empty (pytest
leaves it empty), so nothing is overwritten.

Not copied: `model_versions` and `synthetic_outcomes`. Training state is rebuilt on the
target (`python -m sim demo`), and synthetic rows must not travel with real ones. Uploaded
images are files under backend/uploads, shared by both databases, so they are not copied.
Accounts and password hashes ARE copied, so dev logins work on the test database.

The copy is one transaction on the target: if any table's copied row count differs from the
source's, nothing is kept.
"""

from sqlalchemy import Connection, Engine, func, select, text
from sqlalchemy import Integer as IntegerType
from sqlalchemy.engine import URL

import app.models  # noqa: F401  (registers every table on the metadata)
from app.db import Base

EXCLUDED = frozenset({"model_versions", "synthetic_outcomes"})


class CopyRefused(Exception):
    """The copy was refused before anything was written."""


def copied_tables() -> list:
    """Tables to copy, parents before children (foreign keys are satisfied as rows go in)."""
    return [t for t in Base.metadata.sorted_tables if t.name not in EXCLUDED]


def same_database(a: URL, b: URL) -> bool:
    return (a.host, a.port or 5432, a.database) == (b.host, b.port or 5432, b.database)


def read_only_connection(engine: Engine) -> Connection:
    """A connection whose transaction the database itself holds read-only."""
    return engine.connect().execution_options(postgresql_readonly=True)


def require_empty(target: Connection) -> None:
    for table in copied_tables():
        rows = target.scalar(select(func.count()).select_from(table))
        if rows:
            raise CopyRefused(
                f"The target is not empty: {table.name} has {rows} rows. Run pytest (it drops every table "
                "in the test database and rebuilds it) or otherwise empty it first."
            )


def _require_same_schema_version(source: Connection, target: Connection) -> None:
    query = text("SELECT version_num FROM alembic_version")
    source_version, target_version = source.scalar(query), target.scalar(query)
    if source_version != target_version:
        raise CopyRefused(
            f"Schema versions differ (source {source_version}, target {target_version}). "
            "Run `alembic upgrade head` on the one that is behind."
        )


def _advance_sequences(target: Connection) -> None:
    """Rows were inserted with their own ids, so each integer key's sequence must move past
    the largest one, or the next insert on the target would collide."""
    quote = target.dialect.identifier_preparer.quote
    for table in copied_tables():
        key = list(table.primary_key.columns)
        if len(key) == 1 and isinstance(key[0].type, IntegerType):
            t, c = quote(table.name), quote(key[0].name)
            target.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table.name}', '{key[0].name}'), "
                    f"COALESCE((SELECT MAX({c}) FROM {t}), 1), (SELECT MAX({c}) IS NOT NULL FROM {t}))"
                )
            )


def copy_rows(source: Engine, target: Engine) -> dict[str, tuple[int, int]]:
    """Copy every copied table from source to target. Returns {table: (source rows, target rows)}."""
    if same_database(source.url, target.url):
        raise CopyRefused("The source and the target are the same database.")
    report: dict[str, tuple[int, int]] = {}
    with read_only_connection(source) as src, target.begin() as dst:
        _require_same_schema_version(src, dst)
        require_empty(dst)
        for table in copied_tables():
            rows = [dict(row) for row in src.execute(select(table)).mappings()]
            if rows:
                dst.execute(table.insert(), rows)
            copied = dst.scalar(select(func.count()).select_from(table))
            if copied != len(rows):
                raise CopyRefused(f"{table.name}: copied {copied} rows but the source has {len(rows)}.")
            report[table.name] = (len(rows), copied)
        _advance_sequences(dst)
    return report
