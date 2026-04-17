#!/usr/bin/env bash
# RU: Скрипт явно проверяет миграционный контур первой волны на чистой БД и не зависит от уже поднятого runtime.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
DB_FILE="$TMPDIR/foundation.sqlite3"

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="sqlite+pysqlite:///$DB_FILE"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
export MAGON_FOUNDATION_LEGACY_ENABLED=0

"$REPO_ROOT/.venv/bin/alembic" upgrade head >/dev/null
"$REPO_ROOT/.venv/bin/python" - <<'PY'
import os
import sqlite3
from pathlib import Path

db_url = os.environ["MAGON_FOUNDATION_DATABASE_URL"]
db_path = db_url.removeprefix("sqlite+pysqlite:///")
conn = sqlite3.connect(db_path)
tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
required_tables = {"message_events", "notification_rules", "escalation_hints", "supplier_raw_ingests"}
missing = sorted(required_tables - tables)
if missing:
    raise SystemExit(f"migration_missing_tables:{missing}")
columns = {row[1] for row in conn.execute("PRAGMA table_info('supplier_raw_ingests')")}
required_columns = {"failed_at", "last_retry_at", "retry_count", "failure_code", "failure_detail"}
missing_columns = sorted(required_columns - columns)
if missing_columns:
    raise SystemExit(f"migration_missing_columns:{missing_columns}")
version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
if version != "20260417_0009":
    raise SystemExit(f"unexpected_alembic_head:{version}")
print("migration-check: ok")
PY
