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
- If product-owned files change, at least one relevant file in `docs/ru/` must be updated in the same commit.
- Non-obvious changed logic must get concise Russian comments or docstrings near the code.

## Active Context
<!-- ACTIVE:START -->
- Updated at: `2026-04-17 02:39 +07`
- Branch: `develop`
- Current focus: keep repo guards, Russian docs, and local skills aligned so the workflow cannot silently drift again
- Last verified workflow status: PASS `./scripts/restore_context.sh --check`, PASS `./scripts/verify_workflow.sh --with-web`
- Biggest operational risk: Russian comment quality is now required by policy, but still depends on human review rather than AST-level enforcement
<!-- ACTIVE:END -->

## Recent Worklog
<!-- WORKLOG:START -->
### 2026-04-17 02:39 +07 | develop
- Summary: audit repo guards, skills, and Russian documentation contract end-to-end
- Changed:
  - skills/audit-docs-vs-runtime/SKILL.md, skills/git-safe-commit/SKILL.md, skills/operate-platform/SKILL.md, skills/operate-standalone-intelligence/SKILL.md
  - docs/ru/code-map.md
  - .codex/project-memory.md
- Verified:
  - PASS `./scripts/restore_context.sh --check`
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Russian comment quality is now required by policy, but still depends on human review rather than AST-level enforcement
### 2026-04-17 02:31 +07 | develop
- Summary: enforce Russian documentation layer and Russian code-comment contract
- Changed:
  - docs/ru/README.md, docs/ru/current-project-state.md, docs/ru/repo-workflow.md, docs/ru/code-map.md
  - AGENTS.md, docs/repo-workflow.md, .codex/config.toml
  - .githooks/pre-commit, scripts/restore_context.sh, .codex/project-memory.md
  - Russian comments in apps/web/i18n/request.ts and src/magon_standalone/supplier_intelligence/api.py
- Verified:
  - PASS `./scripts/restore_context.sh --check`
  - PASS `./scripts/verify_workflow.sh --with-web`
  - PASS `cd apps/web && npm run build`
- Risk:
  - the Russian documentation requirement is enforced at commit level, but comment quality still depends on disciplined code review rather than semantic static analysis
### 2026-04-17 02:22 +07 | develop
- Summary: finish locale-aware web shell and localized backend operator surfaces
- Changed:
  - apps/web app pages and navigation
  - apps/web i18n config and locale messages
  - backend supplier_intelligence API localization and locale cookie handling
  - tests.test_api locale coverage
  - .codex/project-memory.md
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
  - PASS `cd apps/web && npm run build`
- Risk:
  - next build emits a cache-invalidation warning from next-intl dynamic import parsing, but the build succeeds and routes are generated
### 2026-04-17 02:08 +07 | develop
- Summary: harden pre-push verification against one-off local test flake
- Changed:
  - .githooks/pre-push
  - .codex/project-memory.md
- Verified:
  - PASS `bash -n .githooks/pre-push`
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - the repo still contains unrelated unstaged product work that must stay outside these workflow commits
### 2026-04-17 02:04 +07 | develop
- Summary: fix pre-push hook empty-argument failure and confirm push path
- Changed:
  - .githooks/pre-push
  - .codex/project-memory.md
- Verified:
  - PASS `bash -n .githooks/pre-push`
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - the repo still contains unrelated unstaged product work that must stay out of this workflow commit set
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
