#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${1:-${MAGON_PLATFORM_BACKEND_URL:-http://127.0.0.1:8091}}"
WEB_URL="${2:-${MAGON_PLATFORM_WEB_URL:-http://127.0.0.1:3000}}"

probe() {
  local label="$1"
  local url="$2"
  local attempts="${3:-3}"
  local timeout="${4:-20}"
  local attempt=1
  while [[ "$attempt" -le "$attempts" ]]; do
    if curl -fsS --max-time "$timeout" "$url" >/dev/null; then
      echo "PASS $label $url"
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  echo "FAIL $label $url" >&2
  return 1
}

# RU: Smoke-чек intentionally узкий: он должен быстро доказать, что backend/web/operator surfaces живы, а не заменить полный test suite.
probe backend-health "$BACKEND_URL/health"
probe backend-status "$BACKEND_URL/status"
probe web-home "$WEB_URL/" 3 20
probe web-dashboard "$WEB_URL/dashboard" 3 20
probe web-ops-workbench "$WEB_URL/ops-workbench" 3 20
probe web-project-map "$WEB_URL/project-map" 3 20
probe operator-companies "$WEB_URL/ui/companies" 3 20
