#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$REPO_ROOT/apps/web"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
ALEMBIC_BIN="$REPO_ROOT/.venv/bin/alembic"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="${MAGON_FOUNDATION_PORT:-8091}"
WEB_HOST="127.0.0.1"
WEB_PORT="3000"
FRESH="0"
SEED="1"

ensure_port_free() {
  local host="$1"
  local port="$2"
  local label="$3"
  if ! "$PYTHON_BIN" - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.2)
try:
    sys.exit(0 if sock.connect_ex((host, port)) != 0 else 1)
finally:
    sock.close()
PY
  then
    # RU: Unified launcher не должен тихо цепляться к чужому процессу на том же порту и объявлять contour "ready" по старому ответу.
    echo "$label port $host:$port is already in use. Stop the existing process first." >&2
    exit 1
  fi
}

usage() {
  cat <<USAGE
Usage: scripts/run_foundation_unified.sh [options]

Starts the wave1 foundation local stack:
- FastAPI foundation backend
- Next.js shell on /

Options:
  --backend-port <port>   Backend port (default: $BACKEND_PORT)
  --web-port <port>       Web port (default: $WEB_PORT)
  --fresh                 Reset foundation DB before migrate+seed
  --no-seed               Skip fixture seeding after migrations
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
    --no-seed)
      SEED="0"; shift ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1 ;;
  esac
done

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Missing Python virtualenv: $PYTHON_BIN" >&2
  echo "Run: python3 -m venv .venv && ./.venv/bin/pip install -e ." >&2
  exit 1
fi

if [[ ! -x "$ALEMBIC_BIN" ]]; then
  echo "Missing alembic in repo virtualenv: $ALEMBIC_BIN" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to run the web shell." >&2
  exit 1
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "[magon-foundation] installing web dependencies"
  (cd "$WEB_DIR" && npm ci)
fi

export MAGON_ENV="${MAGON_ENV:-local}"
export MAGON_FOUNDATION_HOST="$BACKEND_HOST"
export MAGON_FOUNDATION_PORT="$BACKEND_PORT"
export MAGON_API_BASE_URL="http://$BACKEND_HOST:$BACKEND_PORT"
export MAGON_FOUNDATION_LEGACY_ENABLED="${MAGON_FOUNDATION_LEGACY_ENABLED:-false}"
export MAGON_FOUNDATION_DATABASE_URL="${MAGON_FOUNDATION_DATABASE_URL:-postgresql+psycopg://magon:magon@127.0.0.1:5432/magon}"
export MAGON_FOUNDATION_REDIS_URL="${MAGON_FOUNDATION_REDIS_URL:-redis://127.0.0.1:6379/0}"
# RU: Unified startup остаётся каноническим локальным входом и сам доводит infra/runtime до рабочего состояния.
export MAGON_FOUNDATION_CELERY_BROKER_URL="${MAGON_FOUNDATION_CELERY_BROKER_URL:-redis://127.0.0.1:6379/1}"
export MAGON_FOUNDATION_CELERY_RESULT_BACKEND="${MAGON_FOUNDATION_CELERY_RESULT_BACKEND:-redis://127.0.0.1:6379/2}"

ensure_port_free "$BACKEND_HOST" "$BACKEND_PORT" "Backend"
ensure_port_free "$WEB_HOST" "$WEB_PORT" "Web"
"$REPO_ROOT/scripts/ensure_foundation_infra.sh"

if [[ "$FRESH" == "1" ]]; then
  "$PYTHON_BIN" "$REPO_ROOT/scripts/reset_foundation_database.py" --database-url "$MAGON_FOUNDATION_DATABASE_URL"
fi

echo "[magon-foundation] running migrations"
cd "$REPO_ROOT"
"$ALEMBIC_BIN" upgrade head

if [[ "$SEED" == "1" ]]; then
  echo "[magon-foundation] seeding foundation"
  "$PYTHON_BIN" "$REPO_ROOT/scripts/seed_foundation.py" >/tmp/magon-foundation-seed.json
else
  # RU: Desktop launcher и локальные smoke-сценарии должны уметь поднять уже существующую базу без повторного наполнения фикстурами.
  echo "[magon-foundation] skipping seed"
fi

echo "[magon-foundation] starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
"$PYTHON_BIN" "$REPO_ROOT/scripts/run_foundation_api.py" --host "$BACKEND_HOST" --port "$BACKEND_PORT" >/tmp/magon-foundation-backend.log 2>&1 &
BACKEND_PID=$!

cleanup_backend() {
  if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup_backend EXIT INT TERM

for _ in $(seq 1 30); do
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "Foundation backend exited before becoming healthy. See /tmp/magon-foundation-backend.log" >&2
    exit 1
  fi
  if curl -fsS "http://$BACKEND_HOST:$BACKEND_PORT/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -fsS "http://$BACKEND_HOST:$BACKEND_PORT/health/live" >/dev/null 2>&1; then
  echo "Foundation backend failed to become healthy. See /tmp/magon-foundation-backend.log" >&2
  exit 1
fi

echo "[magon-foundation] backend healthy"
cd "$WEB_DIR"
echo "[magon-foundation] starting web shell on http://$WEB_HOST:$WEB_PORT"

MAGON_WEB_DIST_DIR=".next-dev" \
WATCHPACK_POLLING=true \
WATCHPACK_POLLING_INTERVAL=1000 \
npm run dev -- --hostname "$WEB_HOST" --port "$WEB_PORT" &
WEB_PID=$!

cleanup_web() {
  if kill -0 "$WEB_PID" >/dev/null 2>&1; then
    # RU: Unified foundation launcher должен останавливать Next child-process сам, иначе локальный web shell остаётся висеть на порту после Ctrl+C.
    kill "$WEB_PID" >/dev/null 2>&1 || true
    wait "$WEB_PID" 2>/dev/null || true
  fi
}

trap 'cleanup_web; cleanup_backend' EXIT INT TERM

for _ in $(seq 1 60); do
  if ! kill -0 "$WEB_PID" >/dev/null 2>&1; then
    echo "Web shell exited before becoming ready on http://$WEB_HOST:$WEB_PORT/login" >&2
    exit 1
  fi
  if curl -fsS --max-time 5 "http://$WEB_HOST:$WEB_PORT/login" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS --max-time 5 "http://$WEB_HOST:$WEB_PORT/login" >/dev/null 2>&1; then
  echo "Web shell failed to become ready on http://$WEB_HOST:$WEB_PORT/login" >&2
  exit 1
fi

echo "[magon-foundation] web shell ready"
echo "[magon-foundation] foundation login: http://$WEB_HOST:$WEB_PORT/login"
echo "[magon-foundation] public shell: http://$WEB_HOST:$WEB_PORT/"
if [[ "$MAGON_FOUNDATION_LEGACY_ENABLED" == "1" || "$MAGON_FOUNDATION_LEGACY_ENABLED" == "true" || "$MAGON_FOUNDATION_LEGACY_ENABLED" == "yes" || "$MAGON_FOUNDATION_LEGACY_ENABLED" == "on" ]]; then
  echo "[magon-foundation] legacy operator surfaces: http://$WEB_HOST:$WEB_PORT/ui/companies"
fi

wait "$WEB_PID"
