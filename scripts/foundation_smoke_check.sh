#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
PORT="${MAGON_FOUNDATION_PORT:-18191}"
HOST="${MAGON_FOUNDATION_HOST:-127.0.0.1}"
BASE_URL="http://$HOST:$PORT"

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${DB_NAME:-}" ]]; then
    "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" drop --db-name "$DB_NAME" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

"$REPO_ROOT/scripts/ensure_foundation_infra.sh" >/dev/null
eval "$("$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" create --prefix foundation_smoke)"

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="$DATABASE_URL"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
export MAGON_FOUNDATION_LEGACY_ENABLED=0
export MAGON_FOUNDATION_PORT="$PORT"
export MAGON_FOUNDATION_HOST="$HOST"
# RU: Базовый smoke больше не опирается на отдельную SQLite-истину и должен проверять только Postgres-first foundation.

"$REPO_ROOT/.venv/bin/alembic" upgrade head
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-seed.json
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[smoke] health/live"
curl -fsS "$BASE_URL/health/live"
echo

echo "[smoke] health/ready"
curl -fsS "$BASE_URL/health/ready"
echo

echo "[smoke] login"
TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"admin@example.com","password":"admin123"}' | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
echo "token_ok=${#TOKEN}"

echo "[smoke] me"
curl -fsS "$BASE_URL/api/v1/auth/me" -H "authorization: Bearer $TOKEN"
echo
