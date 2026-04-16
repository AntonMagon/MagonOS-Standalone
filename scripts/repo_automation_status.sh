#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"

if ! command -v watchman >/dev/null 2>&1; then
  echo "repo-automation-status: watchman is not installed" >&2
  exit 1
fi

# RU: Этот статус нужен именно для проверки живого watcher-контура, а не только наличия файлов в репозитории.
echo "== Watchman version =="
watchman --version
echo
echo "== Watched roots =="
watchman watch-list
echo
echo "== Repo triggers =="
watchman trigger-list "$REPO_ROOT"
