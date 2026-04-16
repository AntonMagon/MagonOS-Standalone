#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRIGGER_NAME="magonos-repo-auto"

cd "$REPO_ROOT"

if ! command -v watchman >/dev/null 2>&1; then
  echo "install-repo-automation: watchman is not installed" >&2
  exit 1
fi

if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
  echo "install-repo-automation: missing $REPO_ROOT/.venv/bin/python" >&2
  exit 1
fi

watchman watch-project "$REPO_ROOT" >/dev/null
watchman trigger-del "$REPO_ROOT" "$TRIGGER_NAME" >/dev/null 2>&1 || true

# RU: Триггер следит только за source-of-truth путями и не слушает generated root docs/visual outputs, чтобы не устроить autosync loop.
watchman -- trigger "$REPO_ROOT" "$TRIGGER_NAME" \
  'src/**' \
  'scripts/**' \
  'tests/**' \
  'perf/**' \
  # RU: Perf и observability docs тоже включаем в trigger, иначе repo autosync не увидит новый operating layer.
  'apps/web/**' \
  'skills/**' \
  '.githooks/**' \
  'docs/current-project-state.md' \
  'docs/repo-workflow.md' \
  'docs/performance-and-observability.md' \
  'docs/ru/README.md' \
  'docs/ru/current-project-state.md' \
  'docs/ru/repo-workflow.md' \
  'docs/ru/code-map.md' \
  'docs/ru/performance-and-observability.md' \
  '.codex/project-memory.md' \
  '.codex/config.toml' \
  'Taskfile.yml' \
  '.watchmanconfig' \
  -- \
  /usr/bin/env \
  "PYTHONDONTWRITEBYTECODE=1" \
  "$REPO_ROOT/.venv/bin/python" \
  "$REPO_ROOT/scripts/run_repo_autosync.py"

echo "Installed Watchman repo automation for $REPO_ROOT"
watchman trigger-list "$REPO_ROOT"
