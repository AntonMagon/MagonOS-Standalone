#!/usr/bin/env bash
set -euo pipefail

# RU: Это канонический verification path репозитория; перед push/commit он должен ловить drift раньше ручной проверки.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WITH_WEB="0"
PYTHON_BIN="./.venv/bin/python"

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

if [[ ! -x "$PYTHON_BIN" ]]; then
  # RU: В CI и на чистых runner'ах repo-venv может отсутствовать, поэтому verification обязан уметь работать через системный Python.
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

# RU: Проверяем не только shell/python синтаксис, но и то, что repo-level guard scripts вообще запускаемы.
# RU: В verification теперь включён installer project skills, чтобы repo не держал "мертвые" skills без активации в CODEX_HOME.
# RU: Browser automation wrapper тоже входит в канонический contract и не должен выпадать из syntax-check при repo verification.
# RU: Корневые AGENTS.md и README.md тоже считаются продуктовым runtime-контрактом и обязаны быть в синхроне.
# RU: Локальный autosync watcher тоже входит в contract: если его scripts/tests не проходят, background automation уже нельзя считать рабочей.
# RU: Perf/launchd/observability layer тоже должен быть частью канонического verify path, иначе новая автоматизация быстро станет "непроверяемым хвостом".
bash -n \
  scripts/ensure_foundation_infra.sh \
  scripts/install_repo_automation.sh \
  scripts/install_launchd_launcher_watchdog.sh \
  scripts/install_launchd_supplier_scheduler.sh \
  scripts/install_launchd_periodic_checks.sh \
  scripts/launchd_launcher_watchdog_status.sh \
  scripts/launchd_supplier_scheduler_status.sh \
  scripts/run_platform.sh \
  scripts/run_launcher_watchdog.py \
  scripts/run_supplier_scheduler.py \
  scripts/platform_smoke_check.sh \
  scripts/foundation_catalog_smoke_check.sh \
  scripts/foundation_supplier_smoke_check.sh \
  scripts/foundation_request_smoke_check.sh \
  scripts/foundation_offer_smoke_check.sh \
  scripts/foundation_order_smoke_check.sh \
  scripts/foundation_files_documents_smoke_check.sh \
  scripts/foundation_messages_dashboards_smoke_check.sh \
  scripts/foundation_migration_check.sh \
  scripts/foundation_wave1_demo_smoke_check.sh \
  scripts/run_perf_suite.sh \
  scripts/render_launchd_launcher_watchdog.py \
  scripts/render_launchd_supplier_scheduler.py \
  scripts/launchd_periodic_checks_status.sh \
  scripts/render_launchd_periodic_checks.py \
  scripts/run_periodic_checks.py \
  scripts/run_unified_platform.sh \
  scripts/run_playwright_cli.sh \
  scripts/repo_automation_status.sh \
  scripts/restore_context.sh \
  scripts/install_project_skills.sh \
  scripts/install_repo_guards.sh \
  scripts/verify_workflow.sh \
  .githooks/pre-commit \
  .githooks/pre-push

# RU: Detached daemon-helper проверяем как Python entrypoint отдельно от bash syntax-check, иначе launcher drift снова пройдёт мимо канонического verify.
# RU: Postgres-first local helpers тоже держим под compile-check, чтобы launcher/unified/smoke не расходились по DB contract.
"$PYTHON_BIN" -m py_compile \
  scripts/check_russian_locale_integrity.py \
  scripts/manage_temp_foundation_db.py \
  scripts/render_launchd_launcher_watchdog.py \
  scripts/render_launchd_supplier_scheduler.py \
  scripts/render_launchd_periodic_checks.py \
  scripts/run_detached_command.py \
  scripts/run_launcher_watchdog.py \
  scripts/run_supplier_scheduler.py \
  scripts/run_repo_autosync.py \
  scripts/reset_foundation_database.py \
  scripts/run_periodic_checks.py \
  scripts/sync_operating_docs.py \
  src/magon_standalone/launchd_launcher_watchdog.py \
  src/magon_standalone/launchd_supplier_scheduler.py \
  src/magon_standalone/locale_integrity.py \
  src/magon_standalone/launchd_periodic_checks.py \
  src/magon_standalone/observability.py \
  src/magon_standalone/repo_autosync.py \
  src/magon_standalone/operating_docs_sync.py \
  src/magon_standalone/foundation/supplier_scheduler.py

"$PYTHON_BIN" scripts/sync_operating_docs.py --check
# RU: Статический locale-guard режет verify ещё до runtime, если русский source-of-truth снова протёк английскими доменными ярлыками.
"$PYTHON_BIN" scripts/check_russian_locale_integrity.py --static-only
# RU: Имена repo-local skills тоже держим под guard, чтобы automation и ручной вызов skills опирались на один читаемый naming-contract.
"$PYTHON_BIN" scripts/check_skill_naming.py
# RU: Живые Codex automation тоже считаются частью operating-layer, поэтому их id/prompt/cwd/rrule не должны уплывать мимо общего контекста проекта.
"$PYTHON_BIN" scripts/check_automation_contract.py

"$PYTHON_BIN" -m unittest \
  tests.test_foundation_api \
  tests.test_foundation_suppliers \
  tests.test_foundation_catalog \
  tests.test_foundation_draft_request \
  tests.test_foundation_offers \
  tests.test_foundation_orders \
  tests.test_foundation_files_documents \
  tests.test_foundation_events_dashboards \
  tests.test_foundation_llm \
  tests.test_foundation_acceptance \
  tests.test_foundation_migrations \
  tests.test_foundation_seed_repeatable \
  tests.test_persistence \
  tests.test_api \
  tests.test_operations \
  tests.test_workforce \
  tests.test_deploy \
  tests.test_launchd_launcher_watchdog \
  tests.test_supplier_scheduler \
  tests.test_launchd_periodic_checks \
  tests.test_observability \
  tests.test_locale_integrity \
  tests.test_automation_contract \
  tests.test_repo_autosync \
  tests.test_repo_workflow \
  tests.test_skill_naming \
  tests.test_operating_docs_sync \
  tests.test_russian_comment_contract

# RU: Smoke-путь теперь тоже обязан идти по той же Postgres-first схеме, что и launcher/runtime; отдельная SQLite-проверка больше не считается достаточной.
bash ./scripts/foundation_smoke_check.sh
bash ./scripts/foundation_supplier_smoke_check.sh
bash ./scripts/foundation_catalog_smoke_check.sh
bash ./scripts/foundation_request_smoke_check.sh
bash ./scripts/foundation_offer_smoke_check.sh
bash ./scripts/foundation_order_smoke_check.sh
bash ./scripts/foundation_files_documents_smoke_check.sh
bash ./scripts/foundation_messages_dashboards_smoke_check.sh
bash ./scripts/foundation_migration_check.sh
bash ./scripts/foundation_wave1_demo_smoke_check.sh

if [[ "$WITH_WEB" == "1" ]]; then
  # RU: Web-проход остаётся опциональным флагом, чтобы быстрый backend verify и полный shell+web gate жили в одном entrypoint.
  (cd apps/web && npm run typecheck)
fi
