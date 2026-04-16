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

# RU: Перед k6 делаем warmup ключевых страниц, чтобы smoke/load мерял живой runtime, а не первую холодную компиляцию Next dev.
curl -fsS --max-time 20 "$BACKEND_URL/health" >/dev/null
curl -fsS --max-time 20 "$BACKEND_URL/status" >/dev/null
curl -fsS --max-time 20 "$WEB_URL/" >/dev/null
curl -fsS --max-time 20 "$WEB_URL/dashboard" >/dev/null
curl -fsS --max-time 20 "$WEB_URL/ops-workbench" >/dev/null
curl -fsS --max-time 20 "$WEB_URL/project-map" >/dev/null
curl -fsS --max-time 20 "$WEB_URL/ui/companies" >/dev/null

# RU: Perf-прогоны не стартуют платформу сами — они меряют уже живой runtime, чтобы цифры не смешивались со startup noise.
k6 run \
  --summary-export "$SUMMARY_PATH" \
  --env BACKEND_URL="$BACKEND_URL" \
  --env WEB_URL="$WEB_URL" \
  "$SCRIPT_PATH"

echo "k6 summary: $SUMMARY_PATH"
