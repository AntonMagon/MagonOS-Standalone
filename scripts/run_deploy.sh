#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
GUNICORN_BIN="$REPO_ROOT/.venv/bin/gunicorn"
DB_PATH="${MAGON_STANDALONE_DB_PATH:-${SUPPLIER_INTELLIGENCE_DB_PATH:-$REPO_ROOT/data/platform.sqlite3}}"
HOST="${MAGON_STANDALONE_HOST:-0.0.0.0}"
PORT="${PORT:-${MAGON_STANDALONE_PORT:-8091}}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
THREADS="${GUNICORN_THREADS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"
BOOTSTRAP_FIXTURE="${MAGON_STANDALONE_BOOTSTRAP_FIXTURE:-}"
BOOTSTRAP_QUERY="${MAGON_STANDALONE_DEFAULT_QUERY:-printing packaging vietnam}"
BOOTSTRAP_COUNTRY="${MAGON_STANDALONE_DEFAULT_COUNTRY:-VN}"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Missing virtualenv: $VENV_PYTHON" >&2
  echo "Run: python3 -m venv .venv && ./.venv/bin/pip install -e ." >&2
  exit 1
fi

if [[ ! -x "$GUNICORN_BIN" ]]; then
  echo "Missing gunicorn in project venv: $GUNICORN_BIN" >&2
  echo "Run: ./.venv/bin/pip install -e ." >&2
  exit 1
fi

mkdir -p "$(dirname "$DB_PATH")"
export MAGON_STANDALONE_DB_PATH="$DB_PATH"

if [[ -n "$BOOTSTRAP_FIXTURE" && ! -f "$DB_PATH" ]]; then
  if [[ ! -f "$BOOTSTRAP_FIXTURE" ]]; then
    echo "Bootstrap fixture not found: $BOOTSTRAP_FIXTURE" >&2
    exit 1
  fi
  echo "[magon-deploy] bootstrapping DB from fixture"
  "$VENV_PYTHON" "$REPO_ROOT/scripts/run_pipeline.py" \
    --db-path "$DB_PATH" \
    --fixture "$BOOTSTRAP_FIXTURE" \
    --query "$BOOTSTRAP_QUERY" \
    --country "$BOOTSTRAP_COUNTRY"
fi

exec "$GUNICORN_BIN"   --bind "$HOST:$PORT"   --workers "$WEB_CONCURRENCY"   --threads "$THREADS"   --timeout "$TIMEOUT"   --access-logfile -   --error-logfile -   magon_standalone.wsgi:app
