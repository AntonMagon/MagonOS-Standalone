# Project Memory

This file is the versioned project memory for the active standalone repo.
It exists so the project context survives across sessions instead of being re-explained by hand.

## Stable Truth
- Active product repo: `/Users/anton/Desktop/MagonOS-Standalone`
- Legacy donor repo: `/Users/anton/Desktop/MagonOS/MagonOS`
- Standalone is the primary platform-of-record.
- Odoo is donor/bridge context only, not the active runtime.
- Default changes happen only in this repository.
- Current verified contour:
  - company
  - commercial/customer context
  - opportunity
  - quote intent / RFQ boundary
  - production handoff
  - production board
- Already standalone-owned:
  - supplier intelligence pipeline
  - normalization / enrichment / dedup / scoring
  - review queue
  - routing / qualification decisions
  - feedback ledger / projection
  - workforce estimation
- Still dangerous overlap:
  - customer/account identity
  - opportunity/lead ownership
  - RFQ / quote boundary
- Out of scope by default:
  - accounting
  - invoice / payment
  - full ERP order management
  - giant generic CRM
  - broad Odoo entity mirroring
  - Odoo runtime reintroduction
  - source repo feature growth

## Canonical Commands
- Restore context: `./scripts/restore_context.sh`
- Install repo guards: `./scripts/install_repo_guards.sh`
- Backend only: `./scripts/run_platform.sh --fresh --port 8091`
- Unified platform: `./scripts/run_unified_platform.sh --fresh`
- Fixture pipeline: `./.venv/bin/python scripts/run_pipeline.py --fixture tests/fixtures/vn_suppliers_raw.json`
- Backend verification: `./.venv/bin/python -m unittest tests.test_persistence tests.test_api tests.test_operations`
- Workflow verification: `./scripts/verify_workflow.sh`
- Web typecheck when web changed: `cd apps/web && npm run typecheck`
- Finalize a substantial task and persist memory:
  - `./.venv/bin/python scripts/finalize_task.py --summary "..." --changed "..." --verify "./scripts/verify_workflow.sh"`

## Execution Rules
- Substantial work starts with `./scripts/restore_context.sh`.
- Substantial work ends only after project memory is updated and verification is recorded.
- No one should claim GitHub visibility until a real `git push` succeeds.
- Hooks are versioned in `.githooks/` and installed locally through `./scripts/install_repo_guards.sh`.
- If product-owned files change, `.codex/project-memory.md` must be updated in the same commit.

## Active Context
<!-- ACTIVE:START -->
- Updated at: `2026-04-17 01:58 +07`
- Branch: `develop`
- Current focus: use repo memory plus installed hooks as the default start/finish path for substantial work
- Last verified workflow status: PASS `./scripts/verify_workflow.sh`
- Biggest operational risk: repo still has unrelated unstaged product changes in apps/web and supplier_intelligence/api.py that must be staged intentionally
<!-- ACTIVE:END -->

## Recent Worklog
<!-- WORKLOG:START -->
### 2026-04-17 01:58 +07 | develop
- Summary: confirm full repo workflow verification after guard installation
- Changed:
  - .codex/project-memory.md
- Verified:
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - repo still has unrelated unstaged product changes in apps/web and supplier_intelligence/api.py that must be staged intentionally
### 2026-04-17 01:56 +07 | develop
- Summary: install persistent repo memory and enforceable git workflow guards
- Changed:
  - .codex/project-memory.md
  - .githooks/pre-commit and .githooks/pre-push
  - scripts/restore_context.sh, scripts/install_repo_guards.sh, scripts/verify_workflow.sh, scripts/finalize_task.py
  - src/magon_standalone/repo_workflow.py and tests/test_repo_workflow.py
  - AGENTS.md, README.md, .codex/config.toml, docs/repo-workflow.md
- Verified:
  - PASS `./scripts/restore_context.sh --check`
  - PASS `bash -n scripts/run_platform.sh scripts/run_unified_platform.sh scripts/restore_context.sh scripts/install_repo_guards.sh scripts/verify_workflow.sh .githooks/pre-commit .githooks/pre-push`
  - PASS `./.venv/bin/python -m unittest tests.test_repo_workflow`
- Risk:
  - full repo workflow verification still stops on a pre-existing Russian UI expectation mismatch in tests.test_api::test_operator_pages_can_render_in_russian_with_language_cookie
### 2026-04-17 00:00 ICT | bootstrap memory
- Summary: established the initial versioned project memory file for the standalone repo
- Changed:
  - `.codex/project-memory.md`
- Verified:
  - pending
- Risk:
  - this file only helps if the repo workflow updates it on every substantial task
<!-- WORKLOG:END -->
