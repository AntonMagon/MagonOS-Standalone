#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_HOST="${MAGON_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${MAGON_BACKEND_PORT:-8091}"
WEB_HOST="${MAGON_WEB_HOST:-127.0.0.1}"
WEB_PORT="${MAGON_WEB_PORT:-3000}"
DB_PATH="${MAGON_DB_PATH:-$REPO_ROOT/data/platform.sqlite3}"
BACKEND_LOG="/tmp/magon-standalone-backend.log"
WEB_LOG="/tmp/magon-standalone-web.log"
OPEN_BROWSER="1"
SEED_FLAG="--seed"
KEEP_DB="0"
DETACH="0"

usage() {
  cat <<USAGE
Usage: ./Start_Platform.command [options]

Hard-restarts the standalone platform:
- kills anything bound to backend/web ports
- clears local runtime state by default
- starts backend and web shell fresh
- opens the browser when ready

Options:
  --backend-port <port>  Backend port (default: $BACKEND_PORT)
  --web-port <port>      Web port (default: $WEB_PORT)
  --keep-db              Keep the existing SQLite DB
  --no-seed              Do not seed fixture data on backend start
  --no-open              Do not open browser automatically
  --detach               Start in background instead of foreground
  --help                 Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-port)
      BACKEND_PORT="$2"; shift 2 ;;
    --web-port)
      WEB_PORT="$2"; shift 2 ;;
    --keep-db)
      KEEP_DB="1"; shift ;;
    --no-seed)
      SEED_FLAG="--no-seed"; shift ;;
    --no-open)
      OPEN_BROWSER="0"; shift ;;
    --detach)
      DETACH="1"; shift ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1 ;;
  esac
done

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    echo "[magon-restart] stopping port $port: $pids"
    kill $pids 2>/dev/null || true
    sleep 1
    pids="$(lsof -ti "tcp:$port" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      kill -9 $pids 2>/dev/null || true
    fi
  fi
}

start_detached() {
  local log_file="$1"
  local pid_file="$2"
  shift 2
  if command -v setsid >/dev/null 2>&1; then
    setsid "$@" >"$log_file" 2>&1 < /dev/null &
  else
    nohup "$@" >"$log_file" 2>&1 < /dev/null &
  fi
  echo $! >"$pid_file"
}

wait_for_url() {
  local url="$1"
  local label="$2"
  for _ in $(seq 1 60); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      echo "[magon-restart] $label ready: $url"
      return 0
    fi
    sleep 1
  done
  echo "[magon-restart] $label failed to start: $url" >&2
  return 1
}

seed_mode_arg() {
  if [[ "$SEED_FLAG" == "--no-seed" ]]; then
    printf '%s\n' "--no-seed"
  else
    printf '%s\n' "--seed"
  fi
}

if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
  echo "Missing Python virtualenv: $REPO_ROOT/.venv/bin/python" >&2
  echo "Run: python3 -m venv .venv && ./.venv/bin/pip install -e ." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required but not installed." >&2
  exit 1
fi

if [[ ! -d "$REPO_ROOT/apps/web/node_modules" ]]; then
  echo "[magon-restart] installing web dependencies"
  (cd "$REPO_ROOT/apps/web" && npm ci)
fi

kill_port "$WEB_PORT"
kill_port "$BACKEND_PORT"

rm -f "$BACKEND_LOG" "$WEB_LOG"
rm -f /tmp/magon-standalone-backend.pid /tmp/magon-standalone-web.pid
rm -rf "$REPO_ROOT/apps/web/.next"

if [[ "$KEEP_DB" == "0" ]]; then
  echo "[magon-restart] clearing DB $DB_PATH"
  rm -f "$DB_PATH" "$DB_PATH-shm" "$DB_PATH-wal"
fi

mkdir -p "$(dirname "$DB_PATH")"

backend_args=(
  --host "$BACKEND_HOST"
  --port "$BACKEND_PORT"
  --db-path "$DB_PATH"
  "$SEED_FLAG"
)
if [[ "$KEEP_DB" == "0" ]]; then
  backend_args+=(--fresh)
fi

if [[ "$DETACH" == "1" ]]; then
  echo "[magon-restart] starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
  start_detached "$BACKEND_LOG" /tmp/magon-standalone-backend.pid \
    "$REPO_ROOT/scripts/run_platform.sh" "${backend_args[@]}"
  wait_for_url "http://$BACKEND_HOST:$BACKEND_PORT/health" "backend"

  echo "[magon-restart] starting web on http://$WEB_HOST:$WEB_PORT"
  # RU: Detach-ветка должна поднимать тот же устойчивый Next dev runtime, что и канонический run_unified_platform.sh, иначе на macOS снова всплывёт EMFILE.
  start_detached "$WEB_LOG" /tmp/magon-standalone-web.pid \
    /bin/bash -lc "cd '$REPO_ROOT/apps/web' && MAGON_API_BASE_URL='http://$BACKEND_HOST:$BACKEND_PORT' WATCHPACK_POLLING=true WATCHPACK_POLLING_INTERVAL=1000 npm run dev -- --hostname '$WEB_HOST' --port '$WEB_PORT'"
  wait_for_url "http://$WEB_HOST:$WEB_PORT/" "web"

  echo
  echo "Public shell:     http://$WEB_HOST:$WEB_PORT/"
  echo "Ops workbench:    http://$WEB_HOST:$WEB_PORT/ops-workbench"
  echo "Companies:        http://$WEB_HOST:$WEB_PORT/ui/companies"
  echo "Backend health:   http://$BACKEND_HOST:$BACKEND_PORT/health"
  echo "Backend log:      $BACKEND_LOG"
  echo "Web log:          $WEB_LOG"

  if [[ "$OPEN_BROWSER" == "1" ]] && command -v open >/dev/null 2>&1; then
    open "http://$WEB_HOST:$WEB_PORT/" >/dev/null 2>&1 || true
  fi
  exit 0
fi

echo "[magon-restart] launching unified platform in foreground"
if [[ "$OPEN_BROWSER" == "1" ]] && command -v open >/dev/null 2>&1; then
  (sleep 5; open "http://$WEB_HOST:$WEB_PORT/" >/dev/null 2>&1 || true) &
fi

# RU: Foreground-режим всегда идёт через канонический unified entrypoint; этот .command-файл только desktop-обёртка для жёсткого рестарта и автo-open браузера.
unified_args=(
  --backend-port "$BACKEND_PORT"
  --web-port "$WEB_PORT"
  "$(seed_mode_arg)"
)
if [[ "$KEEP_DB" == "0" ]]; then
  unified_args+=(--fresh)
fi

exec "$REPO_ROOT/scripts/run_unified_platform.sh" "${unified_args[@]}"
