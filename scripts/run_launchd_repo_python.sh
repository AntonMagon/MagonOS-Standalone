#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/run_launchd_repo_python.sh <script> [args...]" >&2
  exit 64
fi

SCRIPT_PATH="$1"
shift

export HOME="${HOME:-$(cd ~ && pwd)}"
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"
export PYTHONDONTWRITEBYTECODE=1

cd "$REPO_ROOT"

# RU: Launchd запускает агент в урезанном окружении, поэтому repo-aware wrapper сам фиксирует HOME/CODEX_HOME/PATH
# и всегда исполняет versioned python-скрипт из текущего standalone repo.
exec "$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/$SCRIPT_PATH" "$@"
