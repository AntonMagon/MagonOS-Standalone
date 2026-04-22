#!/usr/bin/env bash
# RU: Скрипт явно проверяет миграционный контур первой волны на чистой БД и не зависит от уже поднятого runtime.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"

cleanup() {
  if [[ -n "${DB_NAME:-}" ]]; then
    "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" drop --db-name "$DB_NAME" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

"$REPO_ROOT/scripts/ensure_foundation_infra.sh" >/dev/null
eval "$("$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" create --prefix foundation_migration)"

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="$DATABASE_URL"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
export MAGON_FOUNDATION_LEGACY_ENABLED=0
# RU: Миграции валидируем на одноразовой Postgres БД, чтобы не портить локальную рабочую схему и всё равно поймать drift.

"$REPO_ROOT/.venv/bin/alembic" upgrade head >/dev/null
"$REPO_ROOT/.venv/bin/python" - <<'PY'
import os
from sqlalchemy import create_engine, inspect, text

db_url = os.environ["MAGON_FOUNDATION_DATABASE_URL"]
engine = create_engine(db_url, future=True)
inspector = inspect(engine)
tables = set(inspector.get_table_names())
required_tables = {"message_events", "notification_rules", "escalation_hints", "supplier_raw_ingests"}
missing = sorted(required_tables - tables)
if missing:
    raise SystemExit(f"migration_missing_tables:{missing}")
columns = {column["name"] for column in inspector.get_columns("supplier_raw_ingests")}
required_columns = {"failed_at", "last_retry_at", "retry_count", "failure_code", "failure_detail"}
missing_columns = sorted(required_columns - columns)
if missing_columns:
    raise SystemExit(f"migration_missing_columns:{missing_columns}")
with engine.connect() as connection:
    version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
if version != "20260417_0010":
    raise SystemExit(f"unexpected_alembic_head:{version}")
print("migration-check: ok")
PY
