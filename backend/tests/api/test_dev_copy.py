"""The dev-to-test copy: it only reads the source, refuses unsafe targets, and covers
every table by decision (copied or explicitly excluded)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db import Base
from app.services import dev_copy
from tests.api import helpers as h


def test_every_table_is_either_copied_or_explicitly_excluded():
    all_tables = {t.name for t in Base.metadata.tables.values()}
    copied = {t.name for t in dev_copy.copied_tables()}
    assert copied | dev_copy.EXCLUDED == all_tables
    assert copied & dev_copy.EXCLUDED == set()
    assert dev_copy.EXCLUDED <= all_tables, "an excluded name that is not a table is a typo"


def test_no_copied_table_depends_on_an_excluded_one():
    """Otherwise its rows would reference data that was not copied."""
    for table in dev_copy.copied_tables():
        parents = {fk.column.table.name for fk in table.foreign_keys}
        assert not parents & dev_copy.EXCLUDED, f"{table.name} references an excluded table"


def test_parents_are_copied_before_their_children():
    order = [t.name for t in dev_copy.copied_tables()]
    for table in dev_copy.copied_tables():
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            if parent != table.name:
                assert order.index(parent) < order.index(table.name), f"{parent} must precede {table.name}"


def test_the_source_connection_is_read_only_so_the_database_refuses_writes(test_engine):
    with dev_copy.read_only_connection(test_engine) as conn:
        with pytest.raises(DBAPIError, match="read-only"):
            conn.execute(text("DELETE FROM users WHERE false"))


def test_copy_refuses_when_source_and_target_are_the_same_database(test_engine):
    with pytest.raises(dev_copy.CopyRefused, match="same database"):
        dev_copy.copy_rows(test_engine, test_engine)


def test_copy_refuses_a_target_that_is_not_empty(client, db):
    conn = db.connection()
    dev_copy.require_empty(conn)  # empty to begin with
    h.donor(client)
    with pytest.raises(dev_copy.CopyRefused, match="not empty"):
        dev_copy.require_empty(conn)
