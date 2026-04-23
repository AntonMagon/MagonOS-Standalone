#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
# RU: Offer smoke держит versioned commercial flow и reset confirmation semantics на активном foundation API.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
HOST="${MAGON_FOUNDATION_HOST:-127.0.0.1}"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  # RU: Smoke оффера не должен зависеть от локального repo-venv, иначе CI краснеет не по бизнес-причине.
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
eval "$("$PYTHON_BIN" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" create --prefix foundation_offer)"

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="$DATABASE_URL"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
PORT="${MAGON_FOUNDATION_PORT:-$(reserve_free_port)}"
export MAGON_FOUNDATION_PORT="$PORT"
export MAGON_FOUNDATION_HOST="$HOST"
BASE_URL="http://$HOST:$PORT"
# RU: Offer smoke обязан повторять тот же Postgres-first flow версий и отправки, что и живой коммерческий контур.
# RU: Свободный порт и bounded health-check не дают versioned offer smoke зависнуть на старом temp API или занятом сокете.

run_alembic upgrade head >/dev/null
"$PYTHON_BIN" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-offer-seed.json
"$PYTHON_BIN" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-offer-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if ! kill -0 "$API_PID" >/dev/null 2>&1; then
    echo "[offer-smoke] foundation API exited before health/live became ready. See /tmp/magon-foundation-offer-api.log" >&2
    exit 1
  fi
  if curl -fsS --max-time 5 "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS --max-time 5 "$BASE_URL/health/live" >/dev/null 2>&1; then
  echo "[offer-smoke] foundation API failed to become ready on $BASE_URL/health/live. See /tmp/magon-foundation-offer-api.log" >&2
  exit 1
fi

TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"operator@example.com","password":"operator123"}' | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

DRAFT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests" \
  -H 'content-type: application/json' \
  -d '{"customer_email":"offer-smoke@example.com","customer_name":"Offer Smoke","title":"Offer smoke draft","summary":"Smoke draft for versioned offer flow.","item_service_context":"Need versioned commercial offer check.","city":"Ho Chi Minh City","requested_deadline_at":"2026-04-30T09:30:00+07:00","intake_channel":"rfq_public","honeypot":"","elapsed_ms":1900}')"

DRAFT_CODE="$(printf '%s' "$DRAFT_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"
REQUEST_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests/$DRAFT_CODE/submit" -H 'content-type: application/json' -d '{"reason_code":"customer_submit_ready_draft"}')"
REQUEST_CODE="$(printf '%s' "$REQUEST_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request"]["code"])')"
CUSTOMER_REF="$(printf '%s' "$REQUEST_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request"]["customer_ref"])')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_status":"needs_review","reason_code":"operator_review_started"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_status":"supplier_search","reason_code":"supplier_search_started"}' >/dev/null

OFFER_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/offers" \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"amount":4200000,"currency_code":"VND","lead_time_days":9,"terms_text":"50% prepayment.","scenario_type":"baseline","public_summary":"Smoke offer v1","comparison_title":"Smoke baseline","comparison_rank":1,"reason_code":"offer_created_from_request"}')"
OFFER_CODE="$(printf '%s' "$OFFER_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["offer"]["code"])')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/send" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"offer_sent_to_customer"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF/offers/$OFFER_CODE/accept" -H 'content-type: application/json' -d '{"reason_code":"customer_acceptance_recorded"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/revise" \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"amount":4500000,"currency_code":"VND","lead_time_days":12,"terms_text":"50% prepayment after reconfirmation.","scenario_type":"revised","public_summary":"Smoke offer v2","comparison_title":"Smoke revised","comparison_rank":1,"reason_code":"offer_critical_revision"}' >/dev/null

DETAIL_JSON="$(curl -fsS "$BASE_URL/api/v1/operator/offers/$OFFER_CODE" -H "authorization: Bearer $TOKEN")"
echo "[offer-smoke] detail"
echo "$DETAIL_JSON"
echo

curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/send" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"offer_sent_to_customer"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF/offers/$OFFER_CODE/accept" -H 'content-type: application/json' -d '{"reason_code":"customer_acceptance_recorded"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/convert-to-order" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"confirmed_offer_converted_to_order"}' >/dev/null

echo "[offer-smoke] final compare"
curl -fsS "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF/offers/compare"
echo
