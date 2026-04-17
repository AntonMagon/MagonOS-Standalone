#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_SCRIPT="$REPO_ROOT/scripts/run_platform.sh"
WEB_DIR="$REPO_ROOT/apps/web"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8091"
WEB_HOST="127.0.0.1"
WEB_PORT="3000"
FRESH="0"
SEED_MODE=""

usage() {
  cat <<USAGE
Usage: scripts/run_unified_platform.sh [options]

Starts the unified MagonOS standalone platform:
- public Next.js shell on /
- operator/runtime console proxied under /ops and /ui

Options:
  --backend-port <port>   Backend port (default: $BACKEND_PORT)
  --web-port <port>       Web port (default: $WEB_PORT)
  --fresh                 Delete local SQLite DB before backend start
  --seed                  Force fixture seeding before backend start
  --no-seed               Skip fixture seeding before backend start
  --help                  Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-port)
      BACKEND_PORT="$2"; shift 2 ;;
    --web-port)
      WEB_PORT="$2"; shift 2 ;;
    --fresh)
      FRESH="1"; shift ;;
    --seed)
      SEED_MODE="--seed"; shift ;;
    --no-seed)
      SEED_MODE="--no-seed"; shift ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1 ;;
  esac
done

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing Python virtualenv: $VENV_PYTHON" >&2
  echo "Run: python3 -m venv .venv && ./.venv/bin/pip install -e ." >&2
  exit 1
fi

if [[ ! -d "$WEB_DIR" ]]; then
  echo "Missing web app directory: $WEB_DIR" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to run the web shell." >&2
  exit 1
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "[magon-unified] installing web dependencies"
  (cd "$WEB_DIR" && npm ci)
fi

backend_args=(--host "$BACKEND_HOST" --port "$BACKEND_PORT")
if [[ "$FRESH" == "1" ]]; then
  backend_args+=(--fresh)
fi
if [[ -n "$SEED_MODE" ]]; then
  backend_args+=("$SEED_MODE")
fi

echo "[magon-unified] starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
"$BACKEND_SCRIPT" "${backend_args[@]}" >/tmp/magon-standalone-backend.log 2>&1 &
BACKEND_PID=$!

cleanup() {
  if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 30); do
  if curl -fsS "http://$BACKEND_HOST:$BACKEND_PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS "http://$BACKEND_HOST:$BACKEND_PORT/health" >/dev/null 2>&1; then
  echo "Backend failed to become healthy. See /tmp/magon-standalone-backend.log" >&2
  exit 1
fi

echo "[magon-unified] backend healthy"
cd "$WEB_DIR"
# RU: На macOS watch limit часто роняет Next dev через EMFILE, поэтому unified shell запускаем с polling-mode по умолчанию.
echo "[magon-unified] starting web shell on http://$WEB_HOST:$WEB_PORT"

MAGON_API_BASE_URL="http://$BACKEND_HOST:$BACKEND_PORT" \
MAGON_WEB_DIST_DIR=".next-dev" \
WATCHPACK_POLLING=true \
WATCHPACK_POLLING_INTERVAL=1000 \
npm run dev -- --hostname "$WEB_HOST" --port "$WEB_PORT" &
WEB_PID=$!

cleanup_web() {
  if kill -0 "$WEB_PID" >/dev/null 2>&1; then
    # RU: Unified launcher должен гасить child Next dev сам, иначе после Ctrl+C остаётся висячий web shell на старом порту.
    kill "$WEB_PID" >/dev/null 2>&1 || true
    wait "$WEB_PID" 2>/dev/null || true
  fi
}

trap 'cleanup_web; cleanup' EXIT INT TERM

for _ in $(seq 1 60); do
  if curl -fsS --max-time 5 "http://$WEB_HOST:$WEB_PORT/" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS --max-time 5 "http://$WEB_HOST:$WEB_PORT/" >/dev/null 2>&1; then
  echo "Web shell failed to become ready on http://$WEB_HOST:$WEB_PORT/" >&2
  exit 1
fi

echo "[magon-unified] web shell ready"
echo "[magon-unified] public shell: http://$WEB_HOST:$WEB_PORT/"
echo "[magon-unified] operator surfaces: http://$WEB_HOST:$WEB_PORT/ops-workbench and http://$WEB_HOST:$WEB_PORT/ui/companies"

wait "$WEB_PID"
