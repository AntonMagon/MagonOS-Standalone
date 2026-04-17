#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
DB_FILE="$TMPDIR/foundation.sqlite3"
PORT="${MAGON_FOUNDATION_PORT:-18193}"
HOST="${MAGON_FOUNDATION_HOST:-127.0.0.1}"
BASE_URL="http://$HOST:$PORT"

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="sqlite+pysqlite:///$DB_FILE"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
export MAGON_FOUNDATION_LEGACY_ENABLED=0
export MAGON_FOUNDATION_PORT="$PORT"
export MAGON_FOUNDATION_HOST="$HOST"

"$REPO_ROOT/.venv/bin/alembic" upgrade head >/dev/null
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-catalog-seed.json
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-catalog-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[catalog-smoke] directions"
curl -fsS "$BASE_URL/api/v1/public/catalog/directions"
echo

CATALOG_JSON="$(curl -fsS "$BASE_URL/api/v1/public/catalog/items")"
echo "[catalog-smoke] items"
echo "$CATALOG_JSON"

READY_CODE="$(printf '%s' "$CATALOG_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; data=json.load(sys.stdin)["items"]; print(next(item["code"] for item in data if item["mode"]=="ready"))')"
echo

echo "[catalog-smoke] detail"
curl -fsS "$BASE_URL/api/v1/public/catalog/items/$READY_CODE"
echo

DRAFT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests" \
  -H 'content-type: application/json' \
  -d "{\"customer_email\":\"catalog-smoke@example.com\",\"customer_name\":\"Catalog Smoke\",\"customer_phone\":\"+84900000001\",\"guest_company_name\":\"Smoke Brand\",\"catalog_item_code\":\"$READY_CODE\",\"title\":\"Запрос по витрине\",\"summary\":\"Нужен быстрый расчёт по карточке витрины.\",\"item_service_context\":\"Контекст карточки витрины для wave1 draft.\",\"city\":\"Ho Chi Minh City\",\"requested_deadline_at\":\"2026-04-27T10:00:00+07:00\",\"intake_channel\":\"catalog_ready\",\"locale_code\":\"ru\",\"honeypot\":\"\",\"elapsed_ms\":1800}")"
echo "[catalog-smoke] draft"
echo "$DRAFT_JSON"
echo

DRAFT_CODE="$(printf '%s' "$DRAFT_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"

echo "[catalog-smoke] submit draft"
curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests/$DRAFT_CODE/submit" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"catalog_smoke_submit","note":"Catalog smoke submit."}'
echo
