#!/usr/bin/env bash
set -euo pipefail

# RU: Скрипт проверяет сквозной контур messages/timeline/notifications/dashboards на живом foundation API.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
PORT="${MAGON_FOUNDATION_PORT:-18198}"
HOST="${MAGON_FOUNDATION_HOST:-127.0.0.1}"
BASE_URL="http://$HOST:$PORT"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  # RU: Smoke событий и панелей не должен зависеть от локального repo-venv, иначе GitHub краснеет на пустом месте.
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
eval "$("$PYTHON_BIN" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" create --prefix foundation_messages)"

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="$DATABASE_URL"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
export MAGON_FOUNDATION_LEGACY_ENABLED=0
export MAGON_FOUNDATION_PORT="$PORT"
export MAGON_FOUNDATION_HOST="$HOST"
# RU: Этот smoke проверяет explainable timeline и notifications на реальном foundation API, а не на тестовой заглушке.

run_alembic upgrade head >/dev/null
"$PYTHON_BIN" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-messages-seed.json
"$PYTHON_BIN" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-messages-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

OPERATOR_TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"operator@example.com","password":"operator123"}' | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
ADMIN_TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"admin@example.com","password":"admin123"}' | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

DRAFT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests" \
  -H 'content-type: application/json' \
  -d '{"customer_email":"messages-smoke@example.com","customer_name":"Messages Smoke","title":"Messages dashboards smoke","summary":"Smoke contour for notifications and dashboards.","item_service_context":"Нужен explainable workflow guard и role-scoped timeline.","city":"Ho Chi Minh City","requested_deadline_at":"2026-05-06T10:30:00+07:00","intake_channel":"rfq_public","honeypot":"","elapsed_ms":2100}')"
DRAFT_CODE="$(printf '%s' "$DRAFT_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"

REQUEST_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests/$DRAFT_CODE/submit" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"customer_submit_ready_draft"}')"
REQUEST_CODE="$(printf '%s' "$REQUEST_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request"]["code"])')"
CUSTOMER_REF="$(printf '%s' "$REQUEST_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request"]["customer_ref"])')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"target_status":"needs_review","reason_code":"operator_review_started"}' >/dev/null

curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"target_status":"needs_clarification","reason_code":"customer_clarification_needed","note":"Нужен artwork и финальный тираж."}' >/dev/null

curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/reasons" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"reason_kind":"blocker","reason_code":"missing_artwork","note":"Artwork still missing."}' >/dev/null

echo "[messages-smoke] customer dashboard"
curl -fsS "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF/dashboard"
echo
echo
echo "[messages-smoke] operator workbench"
curl -fsS "$BASE_URL/api/v1/operator/workbench" -H "authorization: Bearer $OPERATOR_TOKEN"
echo
echo
echo "[messages-smoke] processing dashboard"
curl -fsS "$BASE_URL/api/v1/operator/dashboard/processing" -H "authorization: Bearer $OPERATOR_TOKEN"
echo
echo
echo "[messages-smoke] admin dashboard"
curl -fsS "$BASE_URL/api/v1/admin/dashboard" -H "authorization: Bearer $ADMIN_TOKEN"
echo
echo
echo "[messages-smoke] request timeline"
curl -fsS "$BASE_URL/api/v1/operator/timeline/request/$REQUEST_CODE" -H "authorization: Bearer $OPERATOR_TOKEN"
echo
