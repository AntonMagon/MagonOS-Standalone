#!/usr/bin/env bash
set -euo pipefail

# RU: Этот wrapper не должен рекламировать compatibility-shell как рабочий путь проекта.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
FALLBACK_PYTHON="$(command -v python3 || command -v python || true)"
DEFAULT_DB="$REPO_ROOT/data/platform.sqlite3"
DEFAULT_FIXTURE="$REPO_ROOT/tests/fixtures/vn_suppliers_raw.json"

HOST="127.0.0.1"
PORT="8091"
DB_PATH="$DEFAULT_DB"
FIXTURE_PATH="$DEFAULT_FIXTURE"
QUERY="printing packaging vietnam"
COUNTRY="VN"
SEED_MODE="auto"
FRESH_DB="0"
OPEN_BROWSER="0"

usage() {
  cat <<USAGE
Usage: scripts/run_platform.sh [options]

Starts the standalone MagonOS platform without the old compatibility shell.

Options:
  --host <host>                 Bind host (default: $HOST)
  --port <port>                 Bind port (default: $PORT)
  --db-path <path>              SQLite DB path (default: $DB_PATH)
  --fixture <path>              Fixture file for seeding (default: $FIXTURE_PATH)
  --query <text>                Query used for fixture pipeline seed
  --country <code>              Country code used for fixture pipeline seed
  --seed                        Always seed from fixture before starting API
  --no-seed                     Skip seeding even if DB is missing
  --fresh                       Delete DB file before starting
  --open                        Open the dashboard URL in the browser (macOS open)
  --help                        Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"; shift 2 ;;
    --port)
      PORT="$2"; shift 2 ;;
    --db-path)
      DB_PATH="$2"; shift 2 ;;
    --fixture)
      FIXTURE_PATH="$2"; shift 2 ;;
    --query)
      QUERY="$2"; shift 2 ;;
    --country)
      COUNTRY="$2"; shift 2 ;;
    --seed)
      SEED_MODE="always"; shift ;;
    --no-seed)
      SEED_MODE="never"; shift ;;
    --fresh)
      FRESH_DB="1"; shift ;;
    --open)
      OPEN_BROWSER="1"; shift ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1 ;;
  esac
done

if [[ -x "$VENV_PYTHON" ]]; then
  PYTHON_BIN="$VENV_PYTHON"
elif [[ -n "$FALLBACK_PYTHON" ]]; then
  # RU: В локальном repo по умолчанию предпочитаем versioned .venv, но в CI editable install идёт в runner Python без .venv, и runtime entrypoint не должен падать только из-за этого.
  PYTHON_BIN="$FALLBACK_PYTHON"
else
  echo "Missing Python runtime: $VENV_PYTHON" >&2
  echo "Create it first: python3 -m venv .venv && ./.venv/bin/pip install -e ." >&2
  exit 1
fi

mkdir -p "$(dirname "$DB_PATH")"

if [[ "$FRESH_DB" == "1" && -f "$DB_PATH" ]]; then
  rm -f "$DB_PATH"
fi

should_seed="0"
case "$SEED_MODE" in
  always)
    should_seed="1" ;;
  never)
    should_seed="0" ;;
  auto)
    if [[ ! -f "$DB_PATH" ]]; then
      should_seed="1"
    fi ;;
esac

if [[ "$should_seed" == "1" ]]; then
  if [[ ! -f "$FIXTURE_PATH" ]]; then
    echo "Fixture file not found: $FIXTURE_PATH" >&2
    exit 1
  fi
  echo "[magon-platform] seeding standalone DB from fixture"
  "$PYTHON_BIN" "$REPO_ROOT/scripts/run_pipeline.py" \
    --db-path "$DB_PATH" \
    --fixture "$FIXTURE_PATH" \
    --query "$QUERY" \
    --country "$COUNTRY"
fi

echo "[magon-platform] starting API"
echo "  repo: $REPO_ROOT"
echo "  db:   $DB_PATH"
echo "  url:  http://$HOST:$PORT/"

if [[ "$OPEN_BROWSER" == "1" ]]; then
  (sleep 2; open "http://$HOST:$PORT/") >/dev/null 2>&1 &
fi

exec "$PYTHON_BIN" "$REPO_ROOT/scripts/run_api.py" \
  --host "$HOST" \
  --port "$PORT" \
  --db-path "$DB_PATH" \
  --default-query "$QUERY" \
  --default-country "$COUNTRY"
