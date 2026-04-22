#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"
export MAGON_FOUNDATION_DATABASE_URL="${MAGON_FOUNDATION_DATABASE_URL:-postgresql+psycopg://magon:magon@127.0.0.1:5432/magon}"
# RU: Миграции по умолчанию должны попадать в локальный Postgres contour, а не в отдельную dev-базу по инерции.
"$REPO_ROOT/scripts/ensure_foundation_infra.sh"
exec "$REPO_ROOT/.venv/bin/alembic" upgrade head
