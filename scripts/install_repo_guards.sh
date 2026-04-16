#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

chmod +x \
  .githooks/pre-commit \
  .githooks/pre-push \
  scripts/install_repo_automation.sh \
  scripts/restore_context.sh \
  scripts/install_repo_guards.sh \
  scripts/repo_automation_status.sh \
  scripts/run_repo_autosync.py \
  scripts/verify_workflow.sh

# RU: Repo guards теперь включают и automation entrypoints, чтобы watcher/status scripts не оставались без executable bit после свежего clone.

git config core.hooksPath .githooks

echo "Installed repo guards for $REPO_ROOT"
echo "core.hooksPath=$(git config --get core.hooksPath)"
echo "Restore context with: ./scripts/restore_context.sh"
echo "Verify workflow with: ./scripts/verify_workflow.sh"
