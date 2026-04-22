#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
# RU: Supplier smoke должен проходить на active foundation API, а не на скрытом историческом контуре.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
PORT="${MAGON_FOUNDATION_PORT:-18192}"
HOST="${MAGON_FOUNDATION_HOST:-127.0.0.1}"
BASE_URL="http://$HOST:$PORT"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  # RU: Smoke поставщиков нельзя привязывать к локальному repo-venv, иначе GitHub ловит ложные падения.
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

run_alembic() {
  "$PYTHON_BIN" -m alembic "$@"
}

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${DB_NAME:-}" ]]; then
    "$PYTHON_BIN" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" drop --db-name "$DB_NAME" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

"$REPO_ROOT/scripts/ensure_foundation_infra.sh" >/dev/null
eval "$("$PYTHON_BIN" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" create --prefix foundation_supplier)"

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="$DATABASE_URL"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
export MAGON_FOUNDATION_PORT="$PORT"
export MAGON_FOUNDATION_HOST="$HOST"
# RU: Supplier smoke валидирует тот же ingest/normalization контур, который потом крутит scheduler и operator UI.

run_alembic upgrade head >/dev/null
"$PYTHON_BIN" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-supplier-seed.json
"$PYTHON_BIN" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-supplier-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"operator@example.com","password":"operator123"}' | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
SOURCE_CODE="$(curl -fsS "$BASE_URL/api/v1/operator/supplier-sources" -H "authorization: Bearer $TOKEN" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["items"][0]["code"])')"

echo "[supplier-smoke] run inline ingest"
curl -fsS -X POST "$BASE_URL/api/v1/operator/supplier-ingests/run-inline" \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d "{\"source_registry_code\":\"$SOURCE_CODE\",\"idempotency_key\":\"supplier-smoke-run\",\"reason_code\":\"supplier_smoke_check\"}"
echo

echo "[supplier-smoke] suppliers"
curl -fsS "$BASE_URL/api/v1/operator/suppliers" -H "authorization: Bearer $TOKEN"
echo

echo "[supplier-smoke] raw"
curl -fsS "$BASE_URL/api/v1/operator/supplier-raw" -H "authorization: Bearer $TOKEN"
echo
