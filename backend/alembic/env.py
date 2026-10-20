"""Alembic environment.

Connection, in order of preference:
  1. config.attributes["connection"] — an open connection passed in by tests;
  2. DATABASE_URL via app.config.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.config import get_settings
from app.db import Base, StrEnumType

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """Render StrEnumType as the plain VARCHAR it is, so migrations never import app code."""
    if type_ == "type" and isinstance(obj, StrEnumType):
        return "sa.String(length=32)"
    return False


def _configure(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_item=render_item,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        render_item=render_item,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _configure(connection)
        return
    engine = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    with engine.connect() as conn:
        _configure(conn)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
