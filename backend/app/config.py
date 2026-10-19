"""Application settings — the only place environment variables are read.

Values come from the process environment, falling back to the repo-root `.env`.
Nothing here assumes a container or a particular host.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str
    secret_key: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
