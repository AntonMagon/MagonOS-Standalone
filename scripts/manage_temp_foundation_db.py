#!/usr/bin/env python3
from __future__ import annotations

import argparse
import uuid

import psycopg


def _admin_dsn() -> str:
    return "postgresql://magon:magon@127.0.0.1:5432/postgres"


def create_db(prefix: str) -> int:
    db_name = f"{prefix}_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(_admin_dsn(), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
            cursor.execute(f'CREATE DATABASE "{db_name}"')
    print(f'DB_NAME={db_name}')
    print(f'DATABASE_URL=postgresql+psycopg://magon:magon@127.0.0.1:5432/{db_name}')
    return 0


def drop_db(db_name: str) -> int:
    with psycopg.connect(_admin_dsn(), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or drop a temporary PostgreSQL database for foundation checks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--prefix", default="foundation_tmp")

    drop_parser = subparsers.add_parser("drop")
    drop_parser.add_argument("--db-name", required=True)

    args = parser.parse_args()
    if args.command == "create":
        # RU: Smoke/migration checks должны брать отдельную временную Postgres БД, чтобы verify не трогал основную локальную базу.
        return create_db(args.prefix)
    return drop_db(args.db_name)


if __name__ == "__main__":
    raise SystemExit(main())
