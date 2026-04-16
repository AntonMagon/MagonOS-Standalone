#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIRED_FILES=(
  "AGENTS.md"
  # RU: README теперь тоже часть живого operating-layer и должен восстанавливаться вместе с остальным контекстом.
  "README.md"
  "docs/current-project-state.md"
  "docs/ru/README.md"
  "docs/ru/current-project-state.md"
  ".codex/config.toml"
  ".codex/project-memory.md"
  "docs/repo-workflow.md"
)

check_only="0"

if [[ "${1:-}" == "--check" ]]; then
  check_only="1"
fi

for path in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "$REPO_ROOT/$path" ]]; then
    echo "restore-context: missing required file $path" >&2
    exit 1
  fi
done

hooks_path="$(git -C "$REPO_ROOT" config --get core.hooksPath || true)"
if [[ "$check_only" == "1" ]]; then
  if [[ "$hooks_path" != ".githooks" ]]; then
    echo "restore-context: core.hooksPath is '$hooks_path' but expected '.githooks'" >&2
    exit 1
  fi
  exit 0
fi

echo "== Repo =="
echo "$REPO_ROOT"
echo
echo "== Git Status =="
git -C "$REPO_ROOT" status --short --branch
echo
echo "== Hooks =="
if [[ -n "$hooks_path" ]]; then
  echo "core.hooksPath=$hooks_path"
else
  echo "core.hooksPath is not set"
fi

for path in "${REQUIRED_FILES[@]}"; do
  echo
  echo "== $path =="
  sed -n '1,220p' "$REPO_ROOT/$path"
done
