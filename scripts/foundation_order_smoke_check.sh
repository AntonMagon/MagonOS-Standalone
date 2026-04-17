#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
DB_FILE="$TMPDIR/foundation.sqlite3"
PORT="${MAGON_FOUNDATION_PORT:-18196}"
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
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-order-seed.json
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-order-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"operator@example.com","password":"operator123"}' | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["token"])')"

DRAFT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests" \
  -H 'content-type: application/json' \
  -d '{"customer_email":"order-smoke@example.com","customer_name":"Order Smoke","title":"Order smoke draft","summary":"Smoke draft for order layer.","item_service_context":"Need order lifecycle and payment skeleton check.","city":"Ho Chi Minh City","requested_deadline_at":"2026-04-30T09:30:00+07:00","intake_channel":"rfq_public","honeypot":"","elapsed_ms":1900}')"

DRAFT_CODE="$(printf '%s' "$DRAFT_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"
REQUEST_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests/$DRAFT_CODE/submit" -H 'content-type: application/json' -d '{"reason_code":"customer_submit_ready_draft"}')"
REQUEST_CODE="$(printf '%s' "$REQUEST_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["request"]["code"])')"
CUSTOMER_REF="$(printf '%s' "$REQUEST_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["request"]["customer_ref"])')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_status":"needs_review","reason_code":"operator_review_started"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_status":"supplier_search","reason_code":"supplier_search_started"}' >/dev/null

OFFER_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/offers" \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"amount":5200000,"currency_code":"VND","lead_time_days":11,"terms_text":"50% prepayment.","scenario_type":"baseline","supplier_ref":"SUPC-ORDER","public_summary":"Order smoke offer","comparison_title":"Order smoke baseline","comparison_rank":1,"reason_code":"offer_created_from_request"}')"
OFFER_CODE="$(printf '%s' "$OFFER_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["offer"]["code"])')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/send" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"offer_sent_to_customer"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF/offers/$OFFER_CODE/accept" -H 'content-type: application/json' -d '{"reason_code":"customer_acceptance_recorded"}' >/dev/null

ORDER_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/convert-to-order" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"confirmed_offer_converted_to_order"}')"
ORDER_CODE="$(printf '%s' "$ORDER_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"
LINE_CODE="$(printf '%s' "$ORDER_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["lines"][0]["code"])')"
PAYMENT_CODE="$(printf '%s' "$ORDER_JSON" | "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; print(json.load(sys.stdin)["payments"][0]["code"])')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/orders/$ORDER_CODE/action" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"action":"assign_supplier","supplier_ref":"SUPC-ORDER","reason_code":"order_supplier_assigned"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/orders/$ORDER_CODE/action" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"action":"confirm_start","reason_code":"order_start_confirmed"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/orders/$ORDER_CODE/action" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"action":"mark_production","reason_code":"order_production_marked"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/orders/$ORDER_CODE/action" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d "{\"action\":\"ready\",\"reason_code\":\"order_ready_partial\",\"line_codes\":[\"$LINE_CODE\"]}" >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/payment-records/$PAYMENT_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_state":"pending","reason_code":"payment_pending_bank_transfer"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/payment-records/$PAYMENT_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_state":"confirmed","reason_code":"payment_confirmed_internal"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/payment-records/$PAYMENT_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_state":"partially_refunded","reason_code":"payment_partial_refund_manual"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/orders/$ORDER_CODE/action" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"action":"delivery","reason_code":"order_delivery_marked"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/orders/$ORDER_CODE/action" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"action":"complete","reason_code":"order_completed_internal"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/orders/$ORDER_CODE/action" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"action":"dispute","reason_code":"order_dispute_opened"}' >/dev/null

echo "[order-smoke] detail"
curl -fsS "$BASE_URL/api/v1/operator/orders/$ORDER_CODE" -H "authorization: Bearer $TOKEN"
echo
echo
echo "[order-smoke] customer request"
curl -fsS "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF"
echo
