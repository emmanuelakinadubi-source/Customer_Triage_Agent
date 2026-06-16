from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
if (API_DIR / "app").exists():
    sys.path.insert(0, str(API_DIR))
else:
    sys.path.insert(0, str(ROOT))

load_dotenv(API_DIR / ".env")
load_dotenv(ROOT / ".env")

from app.db.init_db import create_tables  # noqa: E402
from app.db.session import engine  # noqa: E402


def _safe_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    if "@" not in parsed.netloc:
        return raw_url
    userinfo, host = parsed.netloc.rsplit("@", 1)
    username = userinfo.split(":", 1)[0]
    safe_netloc = f"{username}:***@{host}"
    return urlunsplit((parsed.scheme, safe_netloc, parsed.path, parsed.query, parsed.fragment))


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set.")

    print(f"Using database: {_safe_url(database_url)}")
    create_tables()

    with engine.connect() as connection:
        dialect = connection.dialect.name
        if dialect == "postgresql":
            version = connection.execute(text("select version()")).scalar_one()
            ssl_used = connection.execute(
                text(
                    "select ssl from pg_stat_ssl "
                    "where pid = pg_backend_pid()"
                )
            ).scalar_one_or_none()
            table_count = connection.execute(
                text(
                    "select count(*) from information_schema.tables "
                    "where table_schema = 'public' and table_name = 'triage_records'"
                )
            ).scalar_one()
            print(f"Connected to PostgreSQL: {version}")
            print(f"SSL connection: {bool(ssl_used)}")
            print(f"triage_records table present: {bool(table_count)}")
        else:
            result = connection.execute(text("select 1")).scalar_one()
            print(f"Connected to {dialect}; test query returned {result}")


if __name__ == "__main__":
    main()
