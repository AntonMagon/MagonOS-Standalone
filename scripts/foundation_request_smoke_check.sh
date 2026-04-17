#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
DB_FILE="$TMPDIR/foundation.sqlite3"
PORT="${MAGON_FOUNDATION_PORT:-18194}"
HOST="${MAGON_FOUNDATION_HOST:-127.0.0.1}"
BASE_URL="http://$HOST:$PORT"
# RU: Request smoke держим переносимым, чтобы CI проверял сам flow, а не локальную форму запуска python.
source "$REPO_ROOT/scripts/lib_repo_python.sh"
PYTHON_BIN="$(resolve_repo_python "$REPO_ROOT")"

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

run_repo_alembic "$REPO_ROOT" upgrade head >/dev/null
"$PYTHON_BIN" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-request-seed.json
"$PYTHON_BIN" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-request-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"operator@example.com","password":"operator123"}' | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

DRAFT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests" \
  -H 'content-type: application/json' \
  -d '{"customer_email":"request-smoke@example.com","customer_name":"Request Smoke","title":"Smoke draft","summary":"Smoke draft for central intake.","item_service_context":"Need manual request intake for packaging.","city":"Ho Chi Minh City","requested_deadline_at":"2026-04-30T09:30:00+07:00","intake_channel":"web_public","honeypot":"","elapsed_ms":1900}')"
echo "[request-smoke] draft"
echo "$DRAFT_JSON"
echo

DRAFT_CODE="$(printf '%s' "$DRAFT_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"

REQUEST_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests/$DRAFT_CODE/submit" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"customer_submit_ready_draft","note":"Smoke submit."}')"
echo "[request-smoke] request"
echo "$REQUEST_JSON"
echo

REQUEST_CODE="$(printf '%s' "$REQUEST_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request"]["code"])')"

echo "[request-smoke] transition to needs_review"
curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"target_status":"needs_review","reason_code":"operator_review_started","note":"Smoke operator review."}'
echo
