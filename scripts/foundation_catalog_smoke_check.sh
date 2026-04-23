#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
# RU: Catalog smoke доказывает публичный showcase contour без скрытого legacy fallback.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
HOST="${MAGON_FOUNDATION_HOST:-127.0.0.1}"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  # RU: В CI repo-venv может отсутствовать, поэтому smoke обязан падать только по продуктовой причине, а не по пути к Python.
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

run_alembic() {
  "$PYTHON_BIN" -m alembic "$@"
}

reserve_free_port() {
  "$PYTHON_BIN" - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
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
eval "$("$PYTHON_BIN" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" create --prefix foundation_catalog)"

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="$DATABASE_URL"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
PORT="${MAGON_FOUNDATION_PORT:-$(reserve_free_port)}"
export MAGON_FOUNDATION_PORT="$PORT"
export MAGON_FOUNDATION_HOST="$HOST"
BASE_URL="http://$HOST:$PORT"
# RU: Smoke каталога должен идти на временной Postgres БД, иначе витрина проверяется не тем же контуром, что runtime.
# RU: Свободный порт нужен здесь по той же причине, что и в runtime verify: старый зависший temp API не должен ломать public catalog smoke.

run_alembic upgrade head >/dev/null
"$PYTHON_BIN" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-catalog-seed.json
"$PYTHON_BIN" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-catalog-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if ! kill -0 "$API_PID" >/dev/null 2>&1; then
    echo "[catalog-smoke] foundation API exited before health/live became ready. See /tmp/magon-foundation-catalog-api.log" >&2
    exit 1
  fi
  if curl -fsS --max-time 5 "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS --max-time 5 "$BASE_URL/health/live" >/dev/null 2>&1; then
  echo "[catalog-smoke] foundation API failed to become ready on $BASE_URL/health/live. See /tmp/magon-foundation-catalog-api.log" >&2
  exit 1
fi

echo "[catalog-smoke] directions"
curl -fsS "$BASE_URL/api/v1/public/catalog/directions"
echo

CATALOG_JSON="$(curl -fsS "$BASE_URL/api/v1/public/catalog/items")"
echo "[catalog-smoke] items"
echo "$CATALOG_JSON"

READY_CODE="$(printf '%s' "$CATALOG_JSON" | "$PYTHON_BIN" -c 'import json,sys; data=json.load(sys.stdin)["items"]; print(next(item["code"] for item in data if item["mode"]=="ready"))')"
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

DRAFT_CODE="$(printf '%s' "$DRAFT_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"

echo "[catalog-smoke] submit draft"
curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests/$DRAFT_CODE/submit" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"catalog_smoke_submit","note":"Catalog smoke submit."}'
echo
