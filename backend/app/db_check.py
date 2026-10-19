"""Phase 0 connectivity check: `python -m app.db_check` runs SELECT 1 against DATABASE_URL."""

import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import get_settings


def main() -> int:
    url = get_settings().database_url
    safe_url = make_url(url).render_as_string(hide_password=True)
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar_one()
            version = conn.execute(text("SHOW server_version")).scalar_one()
    except Exception as exc:
        print(f"FAILED to reach {safe_url}\n  {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    print(f"OK  {safe_url}  SELECT 1 -> {result}  (PostgreSQL {version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
