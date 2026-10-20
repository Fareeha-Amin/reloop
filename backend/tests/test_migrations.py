"""Migrations: `alembic upgrade head` works on an empty database, downgrades cleanly, and
leaves a schema identical to the models."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

import app.models  # noqa: F401
from app.db import Base
from tests.conftest import alembic_config, drop_everything, upgrade_head

from alembic import command

APP_TABLES = {"users", "organization_profiles", "current_needs", "donations", "donation_images"}


def _tables(engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def test_upgrade_head_on_an_empty_database(test_engine):
    drop_everything(test_engine)
    assert _tables(test_engine) == set()

    upgrade_head(test_engine)
    assert _tables(test_engine) == APP_TABLES | {"alembic_version"}


def test_downgrade_to_base_and_back(test_engine):
    with test_engine.begin() as conn:
        command.downgrade(alembic_config(conn), "base")
    assert _tables(test_engine) - {"alembic_version"} == set()
    upgrade_head(test_engine)
    assert APP_TABLES <= _tables(test_engine)


def test_models_match_migrations(test_engine):
    with test_engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"Models and migrations differ; create a migration:\n{diff}"


def test_only_phase1_tables_exist():
    assert set(Base.metadata.tables) == APP_TABLES
