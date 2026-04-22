#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="$(mktemp -d)"
STORAGE_ROOT="$TMPDIR/storage"
PORT="${MAGON_FOUNDATION_PORT:-18197}"
HOST="${MAGON_FOUNDATION_HOST:-127.0.0.1}"
BASE_URL="http://$HOST:$PORT"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  # RU: Files/documents smoke обязан жить в CI без repo-venv, иначе ловим ложный инфраструктурный fail вместо продуктового.
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
eval "$("$PYTHON_BIN" "$REPO_ROOT/scripts/manage_temp_foundation_db.py" create --prefix foundation_files_docs)"

export MAGON_ENV=test
export MAGON_FOUNDATION_DATABASE_URL="$DATABASE_URL"
export MAGON_FOUNDATION_REDIS_URL=""
export MAGON_FOUNDATION_CELERY_BROKER_URL="memory://"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="cache+memory://"
export MAGON_FOUNDATION_LEGACY_ENABLED=0
export MAGON_FOUNDATION_STORAGE_BACKEND=local
export MAGON_FOUNDATION_STORAGE_LOCAL_ROOT="$STORAGE_ROOT"
export MAGON_FOUNDATION_PORT="$PORT"
export MAGON_FOUNDATION_HOST="$HOST"
# RU: Files/documents smoke держим на Postgres-first пути, чтобы версии, архив и аудит совпадали с боевым потоком.

printf 'brief-v1\n' >"$TMPDIR/brief-v1.txt"
printf 'brief-v2\n' >"$TMPDIR/brief-v2.txt"

run_alembic upgrade head >/dev/null
"$PYTHON_BIN" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-files-docs-seed.json
"$PYTHON_BIN" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$HOST" --port "$PORT" >/tmp/magon-foundation-files-docs-api.log 2>&1 &
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
  -d '{"customer_email":"files-docs-smoke@example.com","customer_name":"Files Docs Smoke","title":"Files docs smoke draft","summary":"Smoke draft for files/documents.","item_service_context":"Need managed file/doc checks for request, offer and order.","city":"Ho Chi Minh City","requested_deadline_at":"2026-05-04T10:00:00+07:00","intake_channel":"rfq_public","honeypot":"","elapsed_ms":2200}')"

DRAFT_CODE="$(printf '%s' "$DRAFT_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"
REQUEST_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/public/draft-requests/$DRAFT_CODE/submit" -H 'content-type: application/json' -d '{"reason_code":"customer_submit_ready_draft"}')"
REQUEST_CODE="$(printf '%s' "$REQUEST_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request"]["code"])')"
CUSTOMER_REF="$(printf '%s' "$REQUEST_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["request"]["customer_ref"])')"

UPLOAD_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/files/upload" \
  -H "authorization: Bearer $TOKEN" \
  -F "owner_type=request" \
  -F "owner_code=$REQUEST_CODE" \
  -F "file_type=brief" \
  -F "visibility_scope=customer" \
  -F "reason_code=request_file_uploaded" \
  -F "upload=@$TMPDIR/brief-v1.txt;type=text/plain")"
ASSET_CODE="$(printf '%s' "$UPLOAD_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/files/$ASSET_CODE/versions" \
  -H "authorization: Bearer $TOKEN" \
  -F "reason_code=request_file_reuploaded" \
  -F "upload=@$TMPDIR/brief-v2.txt;type=text/plain" >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/files/$ASSET_CODE/review" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_state":"passed","reason_code":"file_manual_review_approved"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/files/$ASSET_CODE/finalize" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"file_final_version_confirmed"}' >/dev/null

curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_status":"needs_review","reason_code":"operator_review_started"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/transition" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"target_status":"supplier_search","reason_code":"supplier_search_started"}' >/dev/null

OFFER_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE/offers" \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"amount":3500000,"currency_code":"VND","lead_time_days":8,"terms_text":"50% prepayment.","scenario_type":"baseline","supplier_ref":"SUPC-FILEDOC","public_summary":"Files/docs smoke offer","comparison_title":"Files/docs baseline","comparison_rank":1,"reason_code":"offer_created_from_request"}')"
OFFER_CODE="$(printf '%s' "$OFFER_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["offer"]["code"])')"

DOCUMENT_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/documents/generate" \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d "{\"owner_type\":\"offer\",\"owner_code\":\"$OFFER_CODE\",\"template_key\":\"offer_proposal\",\"reason_code\":\"offer_document_generated\"}")"
DOCUMENT_CODE="$(printf '%s' "$DOCUMENT_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"
curl -fsS -X POST "$BASE_URL/api/v1/operator/documents/$DOCUMENT_CODE/send" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"document_sent_to_customer"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/documents/$DOCUMENT_CODE/confirm" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"document_confirmation_recorded"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/operator/documents/$DOCUMENT_CODE/replace" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"document_replaced_after_revision"}' >/dev/null

curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/send" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"offer_sent_to_customer"}' >/dev/null
curl -fsS -X POST "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF/offers/$OFFER_CODE/accept" -H 'content-type: application/json' -d '{"reason_code":"customer_acceptance_recorded"}' >/dev/null
ORDER_JSON="$(curl -fsS -X POST "$BASE_URL/api/v1/operator/offers/$OFFER_CODE/convert-to-order" -H "authorization: Bearer $TOKEN" -H 'content-type: application/json' -d '{"reason_code":"confirmed_offer_converted_to_order"}')"
ORDER_CODE="$(printf '%s' "$ORDER_JSON" | "$PYTHON_BIN" -c 'import json,sys; print(json.load(sys.stdin)["item"]["code"])')"

curl -fsS -X POST "$BASE_URL/api/v1/operator/documents/generate" \
  -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d "{\"owner_type\":\"order\",\"owner_code\":\"$ORDER_CODE\",\"template_key\":\"internal_job\",\"reason_code\":\"order_document_generated\"}" >/dev/null

echo "[files-docs-smoke] request detail"
curl -fsS "$BASE_URL/api/v1/operator/requests/$REQUEST_CODE" -H "authorization: Bearer $TOKEN"
echo
echo
echo "[files-docs-smoke] order detail"
curl -fsS "$BASE_URL/api/v1/operator/orders/$ORDER_CODE" -H "authorization: Bearer $TOKEN"
echo
echo
echo "[files-docs-smoke] customer request"
curl -fsS "$BASE_URL/api/v1/public/requests/$CUSTOMER_REF"
echo
