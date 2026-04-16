#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WITH_WEB="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-web)
      WITH_WEB="1"; shift ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1 ;;
  esac
done

cd "$REPO_ROOT"

bash -n \
  scripts/run_platform.sh \
  scripts/run_unified_platform.sh \
  scripts/restore_context.sh \
  scripts/install_repo_guards.sh \
  scripts/verify_workflow.sh \
  .githooks/pre-commit \
  .githooks/pre-push

./.venv/bin/python -m unittest \
  tests.test_persistence \
  tests.test_api \
  tests.test_operations \
  tests.test_workforce \
  tests.test_deploy \
  tests.test_repo_workflow

if [[ "$WITH_WEB" == "1" ]]; then
  (cd apps/web && npm run typecheck)
fi
