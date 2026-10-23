"""Application settings — the only place environment variables are read.

Values come from the process environment, falling back to the repo-root `.env`.
Nothing here assumes a container or a particular host.

Only environment-specific values belong here (connection strings, secrets). Domain
vocabularies and tunables live in `app.constants`.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str
    secret_key: str
    # Separate database for pytest. Tests that need a database are skipped (with the
    # reason shown) when this is unset, and refuse to run if it names DATABASE_URL's
    # database, because the test setup drops every table in it.
    test_database_url: str | None = None
    # Run the deadline sweeper in-process, every SWEEP_INTERVAL (app.main lifespan).
    # The test suite sets it false; manual runs use the CLI or POST /admin/sweep.
    sweeper_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
