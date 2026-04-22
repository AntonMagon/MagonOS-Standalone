#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine, text


def _default_database_url(repo_root: Path) -> str:
    return f"postgresql+psycopg://magon:magon@127.0.0.1:5432/magon"


def _reset_sqlite(database_url: str) -> None:
    db_path = Path(database_url.removeprefix("sqlite+pysqlite:///"))
    for candidate in (db_path, db_path.with_name(f"{db_path.name}-shm"), db_path.with_name(f"{db_path.name}-wal")):
        if candidate.exists():
            candidate.unlink()


def _reset_postgres(database_url: str) -> None:
    engine = create_engine(database_url, future=True, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        # RU: Для локального Postgres-first launcher достаточно полностью пересобрать public schema, чтобы `--fresh` оставался простым и предсказуемым.
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Reset the foundation database for a fresh local start.")
    parser.add_argument("--database-url", default=os.environ.get("MAGON_FOUNDATION_DATABASE_URL", _default_database_url(repo_root)))
    args = parser.parse_args()

    database_url = args.database_url
    if database_url.startswith("sqlite+pysqlite:///"):
        _reset_sqlite(database_url)
    elif database_url.startswith("postgresql"):
        _reset_postgres(database_url)
    else:
        raise SystemExit(f"unsupported_database_url:{database_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
