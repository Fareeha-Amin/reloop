"""Shared fixtures.

Unit tests need nothing. Tests that use `db`, `client` or `test_engine` need
TEST_DATABASE_URL: a separate database whose tables are DROPPED at the start of the run.
Without it they are skipped, with the reason shown in the pytest summary.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.main import app
from app.services.storage import LocalImageStorage, get_storage

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _same_database(a: str, b: str) -> bool:
    ua, ub = make_url(a), make_url(b)
    return (ua.host, ua.port or 5432, ua.database) == (ub.host, ub.port or 5432, ub.database)


def alembic_config(connection) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["connection"] = connection
    cfg.attributes["configure_logger"] = False
    return cfg


def drop_everything(engine: Engine) -> None:
    """Drop every table in the test database, including alembic_version."""
    meta = MetaData()
    meta.reflect(bind=engine)
    meta.drop_all(bind=engine)


def upgrade_head(engine: Engine) -> None:
    with engine.begin() as conn:
        command.upgrade(alembic_config(conn), "head")


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    settings = get_settings()
    url = settings.test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; database tests skipped.")
    if _same_database(url, settings.database_url):
        pytest.exit(
            "TEST_DATABASE_URL points at the same database as DATABASE_URL. Refusing to run: "
            "the test setup drops every table.",
            returncode=4,
        )
    engine = create_engine(url)
    drop_everything(engine)
    upgrade_head(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(test_engine: Engine) -> Iterator[Session]:
    """A session inside a transaction that is rolled back after the test. Service-level
    commits become savepoint releases, so nothing a test writes survives it."""
    connection = test_engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def storage(tmp_path) -> LocalImageStorage:
    return LocalImageStorage(tmp_path / "uploads")


@pytest.fixture
def client(db: Session, storage: LocalImageStorage) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_storage] = lambda: storage
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
