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

# RU: Launcher и standalone runtime больше не обязаны держать legacy `/status` и `/ui/*`,
# поэтому smoke фиксируем на актуальном wave1 contour, который реально должен жить после старта.
probe backend-health "$BACKEND_URL/health/ready"
probe backend-system-mode "$BACKEND_URL/api/v1/meta/system-mode"
probe web-home "$WEB_URL/" 3 20
probe web-login "$WEB_URL/login" 3 20
probe web-marketing "$WEB_URL/marketing" 3 20
# RU: Project map теперь часть канонического shell surface, поэтому проверяем его тем же smoke-контуром, что и рабочие operator страницы.
probe web-project-map "$WEB_URL/project-map" 3 20
probe web-request-workbench "$WEB_URL/request-workbench" 3 20
probe web-orders "$WEB_URL/orders" 3 20
probe web-suppliers "$WEB_URL/suppliers" 3 20
