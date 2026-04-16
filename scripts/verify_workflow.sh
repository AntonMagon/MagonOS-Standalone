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

# RU: Проверяем не только shell/python синтаксис, но и то, что repo-level guard scripts вообще запускаемы.
# RU: В verification теперь включён installer project skills, чтобы repo не держал "мертвые" skills без активации в CODEX_HOME.
# RU: Browser automation wrapper тоже входит в канонический contract и не должен выпадать из syntax-check при repo verification.
# RU: Корневые AGENTS.md и README.md тоже считаются продуктовым runtime-контрактом и обязаны быть в синхроне.
# RU: Локальный autosync watcher тоже входит в contract: если его scripts/tests не проходят, background automation уже нельзя считать рабочей.
bash -n \
  scripts/install_repo_automation.sh \
  scripts/run_platform.sh \
  scripts/run_unified_platform.sh \
  scripts/run_playwright_cli.sh \
  scripts/repo_automation_status.sh \
  scripts/restore_context.sh \
  scripts/install_project_skills.sh \
  scripts/install_repo_guards.sh \
  scripts/verify_workflow.sh \
  .githooks/pre-commit \
  .githooks/pre-push

./.venv/bin/python -m py_compile \
  scripts/run_repo_autosync.py \
  scripts/sync_operating_docs.py \
  src/magon_standalone/repo_autosync.py \
  src/magon_standalone/operating_docs_sync.py

./.venv/bin/python scripts/sync_operating_docs.py --check

./.venv/bin/python -m unittest \
  tests.test_persistence \
  tests.test_api \
  tests.test_operations \
  tests.test_workforce \
  tests.test_deploy \
  tests.test_repo_autosync \
  tests.test_repo_workflow \
  tests.test_operating_docs_sync \
  tests.test_russian_comment_contract

if [[ "$WITH_WEB" == "1" ]]; then
  (cd apps/web && npm run typecheck)
fi
