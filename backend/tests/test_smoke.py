"""Phase 0 smoke tests. Neither touches the database."""

from app.config import Settings


def test_pytest_runs():
    assert 1 + 1 == 2


def test_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db.example:5432/x")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@db.example:5432/x"
    assert settings.secret_key == "test-secret"
