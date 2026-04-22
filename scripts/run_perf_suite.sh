#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENARIO="${1:-smoke}"
BACKEND_URL="${MAGON_PLATFORM_BACKEND_URL:-http://127.0.0.1:8091}"
WEB_URL="${MAGON_PLATFORM_WEB_URL:-http://127.0.0.1:3000}"
OUTPUT_DIR="${REPO_ROOT}/.cache/perf"
SCRIPT_PATH=""

usage() {
  cat <<USAGE
Usage: scripts/run_perf_suite.sh <smoke|load|stress>

Runs repo-versioned k6 scenarios against the current local MagonOS platform.

Environment:
  MAGON_PLATFORM_BACKEND_URL   Backend base URL (default: $BACKEND_URL)
  MAGON_PLATFORM_WEB_URL       Web base URL (default: $WEB_URL)
USAGE
}

case "$SCENARIO" in
  smoke)
    SCRIPT_PATH="$REPO_ROOT/perf/k6/smoke.js" ;;
  load)
    SCRIPT_PATH="$REPO_ROOT/perf/k6/load.js" ;;
  stress)
    SCRIPT_PATH="$REPO_ROOT/perf/k6/stress.js" ;;
  --help|-h)
    usage; exit 0 ;;
  *)
    echo "Unknown scenario: $SCENARIO" >&2
    usage >&2
    exit 1 ;;
esac

if ! command -v k6 >/dev/null 2>&1; then
  echo "run-perf-suite: k6 is not installed" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
SUMMARY_PATH="$OUTPUT_DIR/${SCENARIO}-summary.json"

warmup_probe() {
  local url="$1"
  local attempts="${2:-3}"
  local timeout="${3:-30}"
  local attempt=1
  # RU: Warmup intentionally ретраит URL до старта k6, чтобы первое холодное обращение к Next dev не выглядело как runtime/perf-регрессия.
  while [[ "$attempt" -le "$attempts" ]]; do
    if curl -fsS --max-time "$timeout" "$url" >/dev/null; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  echo "run-perf-suite: warmup failed for $url" >&2
  return 1
}

# RU: Перед k6 прогреваем только канонические foundation URL, а не legacy /status или donor-era UI маршруты.
warmup_probe "$BACKEND_URL/health/live" 2 15
warmup_probe "$BACKEND_URL/health/ready" 2 15
warmup_probe "$BACKEND_URL/api/v1/meta/system-mode" 2 15
warmup_probe "$BACKEND_URL/api/v1/public/catalog/items" 2 15
warmup_probe "$WEB_URL/" 3 30
warmup_probe "$WEB_URL/login" 3 30
warmup_probe "$WEB_URL/marketing" 3 30
warmup_probe "$WEB_URL/request-workbench" 3 30
warmup_probe "$WEB_URL/orders" 3 30
warmup_probe "$WEB_URL/suppliers" 3 30

# RU: Perf-прогоны не стартуют платформу сами — они меряют уже живой runtime, чтобы цифры не смешивались со startup noise.
k6 run \
  --summary-export "$SUMMARY_PATH" \
  --env BACKEND_URL="$BACKEND_URL" \
  --env WEB_URL="$WEB_URL" \
  "$SCRIPT_PATH"

echo "k6 summary: $SUMMARY_PATH"
