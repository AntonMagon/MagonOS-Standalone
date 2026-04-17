#!/usr/bin/env bash
# RU: Скрипт собирает единый демонстрационный поток первой волны на одной временной БД без разрыва по шагам.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
DB_FILE="$TMPDIR/foundation.sqlite3"
STORAGE_DIR="$TMPDIR/storage"
FILE_V1="$TMPDIR/wave1-demo-v1.txt"
FILE_V2="$TMPDIR/wave1-demo-v2.txt"
PORT="${MAGON_FOUNDATION_PORT:-18198}"
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
export MAGON_FOUNDATION_STORAGE_BACKEND="local"
export MAGON_FOUNDATION_STORAGE_LOCAL_ROOT="$STORAGE_DIR"
export MAGON_FOUNDATION_PORT="$PORT"
export MAGON_FOUNDATION_HOST="$HOST"

printf 'wave1-demo-v1' >"$FILE_V1"
printf 'wave1-demo-v2' >"$FILE_V2"

"$REPO_ROOT/.venv/bin/alembic" upgrade head >/dev/null
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-wave1-demo-seed.json
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-wave1-demo-api.log 2>&1 &
API_PID=$!

for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

json_get() {
  local expr="$1"
  "$REPO_ROOT/.venv/bin/python" -c 'import json,sys; data=json.load(sys.stdin); expr=sys.argv[1]; print(eval(expr, {"data": data}))' "$expr"
}

OPERATOR_TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"operator@example.com","password":"operator123"}' | json_get 'data["token"]')"
ADMIN_TOKEN="$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'content-type: application/json' -d '{"email":"admin@example.com","password":"admin123"}' | json_get 'data["token"]')"
SOURCE_CODE="$(curl -fsS "$BASE_URL/api/v1/operator/supplier-sources" -H "authorization: Bearer $OPERATOR_TOKEN" | json_get 'data["items"][0]["code"]')"

echo "[wave1-demo] supplier ingest -> normalized supplier"
INGEST_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/supplier-ingests/run-inline" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d "{\"source_registry_code\":\"$SOURCE_CODE\",\"idempotency_key\":\"wave1-demo-ingest\",\"reason_code\":\"supplier_demo_ingest\"}")"
INGEST_CODE="$(printf '%s' "$INGEST_JSON" | json_get 'data["item"]["ingest_code"]')"

echo "[wave1-demo] storefront -> draft"
DRAFT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests" \
  -H 'content-type: application/json' \
  -d '{"customer_email":"wave1-demo@example.com","customer_name":"Wave1 Demo","title":"Wave1 acceptance demo","summary":"Unified demo flow for first wave acceptance.","item_service_context":"Need storefront-to-order flow with files, docs, timeline and dashboards.","city":"Ho Chi Minh City","requested_deadline_at":"2026-05-05T10:00:00+07:00","intake_channel":"rfq_public","honeypot":"","elapsed_ms":2400}')"
DRAFT_CODE="$(printf '%s' "$DRAFT_JSON" | json_get 'data["item"]["code"]')"

echo "[wave1-demo] draft -> request"
REQUEST_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests/$DRAFT_CODE/submit" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"customer_submit_ready_draft","note":"Demo submit."}')"
REQUEST_CODE="$(printf '%s' "$REQUEST_JSON" | json_get 'data["request"]["code"]')"
CUSTOMER_REF="$(printf '%s' "$REQUEST_JSON" | json_get 'data["request"]["customer_ref"]')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"target_status":"needs_review","reason_code":"operator_review_started"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"target_status":"supplier_search","reason_code":"supplier_search_started"}' >/dev/null

echo "[wave1-demo] request -> versioned offer"
OFFER_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/offers" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"amount":4200000,"currency_code":"VND","lead_time_days":9,"terms_text":"50% prepayment.","scenario_type":"baseline","supplier_ref":"SUPC-DEMO","public_summary":"Wave1 demo offer","comparison_title":"Demo baseline","comparison_rank":1,"reason_code":"offer_created_from_request"}')"
OFFER_CODE="$(printf '%s' "$OFFER_JSON" | json_get 'data["offer"]["code"]')"
curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/send" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"offer_sent_to_customer"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF/offers/$OFFER_CODE/accept" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"customer_acceptance_recorded"}' >/dev/null

echo "[wave1-demo] accepted offer -> order"
ORDER_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/convert-to-order" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"confirmed_offer_converted_to_order"}')"
ORDER_CODE="$(printf '%s' "$ORDER_JSON" | json_get 'data["item"]["code"]')"

echo "[wave1-demo] file/document version flow"
FILE_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/files/upload" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -F owner_type=request \
  -F owner_code="$REQUEST_CODE" \
  -F file_type=brief \
  -F visibility_scope=customer \
  -F reason_code=request_file_uploaded \
  -F "upload=@$FILE_V1;type=text/plain")"
FILE_CODE="$(printf '%s' "$FILE_JSON" | json_get 'data["item"]["code"]')"
curl -fsS -X POST "$BASE_URL/api/v1/operator/files/$FILE_CODE/versions" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -F reason_code=request_file_reuploaded \
  -F "upload=@$FILE_V2;type=text/plain" >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/files/$FILE_CODE/review" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"target_state":"approved","reason_code":"file_manual_review_approved"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/files/$FILE_CODE/finalize" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"file_final_version_confirmed"}' >/dev/null
DOCUMENT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/documents/generate" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d "{\"owner_type\":\"offer\",\"owner_code\":\"$OFFER_CODE\",\"template_key\":\"offer_proposal\",\"reason_code\":\"offer_document_generated\"}")"
DOCUMENT_CODE="$(printf '%s' "$DOCUMENT_JSON" | json_get 'data["item"]["code"]')"
curl -fsS -X POST "$BASE_URL/api/v1/operator/documents/$DOCUMENT_CODE/send" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"document_sent_to_customer"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/documents/$DOCUMENT_CODE/confirm" \
  -H "authorization: Bearer $OPERATOR_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"reason_code":"document_confirmation_recorded"}' >/dev/null

echo "[wave1-demo] timeline/audit visibility and dashboards"
PUBLIC_REQUEST="$(curl -fsS "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF")"
CUSTOMER_DASHBOARD="$(curl -fsS "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF/dashboard")"
TIMELINE="$(curl -fsS "$BASE_URL/api/v1/operator/timeline/request/$REQUEST_CODE" -H "authorization: Bearer $OPERATOR_TOKEN")"
AUDIT="$(curl -fsS "$BASE_URL/api/v1/operator/audit/events" -H "authorization: Bearer $OPERATOR_TOKEN")"
ADMIN_DASHBOARD="$(curl -fsS "$BASE_URL/api/v1/admin/dashboard" -H "authorization: Bearer $ADMIN_TOKEN")"
SUPPLY_DASHBOARD="$(curl -fsS "$BASE_URL/api/v1/operator/dashboard/supply" -H "authorization: Bearer $OPERATOR_TOKEN")"
PROCESSING_DASHBOARD="$(curl -fsS "$BASE_URL/api/v1/operator/dashboard/processing" -H "authorization: Bearer $OPERATOR_TOKEN")"
INGEST_DETAIL="$(curl -fsS "$BASE_URL/api/v1/operator/supplier-ingests/$INGEST_CODE" -H "authorization: Bearer $OPERATOR_TOKEN")"

export PUBLIC_REQUEST CUSTOMER_DASHBOARD TIMELINE AUDIT ADMIN_DASHBOARD SUPPLY_DASHBOARD PROCESSING_DASHBOARD INGEST_DETAIL

"$REPO_ROOT/.venv/bin/python" - <<'PY'
import json
import os

public_request = json.loads(os.environ["PUBLIC_REQUEST"])
customer_dashboard = json.loads(os.environ["CUSTOMER_DASHBOARD"])
timeline = json.loads(os.environ["TIMELINE"])
audit = json.loads(os.environ["AUDIT"])
admin_dashboard = json.loads(os.environ["ADMIN_DASHBOARD"])
supply_dashboard = json.loads(os.environ["SUPPLY_DASHBOARD"])
processing_dashboard = json.loads(os.environ["PROCESSING_DASHBOARD"])
ingest_detail = json.loads(os.environ["INGEST_DETAIL"])

assert public_request["item"]["order"]["code"], "order should be visible in public request"
assert len(public_request["item"]["documents"]) == 1, "customer document should be visible"
actions = {item["action"] for item in audit["items"]}
for required in {"ingest_completed", "draft_submitted", "offer_created", "order_created", "file_uploaded", "document_generated"}:
    assert required in actions, f"missing audit action: {required}"
timeline_codes = {item["entry_kind"] for item in timeline["items"]}
assert "event" in timeline_codes, "timeline should include events"
assert admin_dashboard["counts"]["message_events"] >= 1, "admin dashboard should expose message events"
assert "trusted" in supply_dashboard["suppliers_by_trust"], "supply dashboard should expose trust buckets"
assert processing_dashboard["requests_by_status"], "processing dashboard should expose request buckets"
assert ingest_detail["ingest"]["ingest_status"] == "completed", "supplier ingest should finish"
print(json.dumps({
    "request_code": public_request["item"]["code"],
    "customer_ref": public_request["item"]["customer_ref"],
    "order_code": public_request["item"]["order"]["code"],
    "ingest_code": ingest_detail["ingest"]["code"],
    "timeline_items": len(timeline["items"]),
    "audit_actions": sorted(list(actions))[:8],
}, ensure_ascii=False))
PY
