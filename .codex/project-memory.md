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
- Changed code files must include added `RU:` explanatory lines in the staged diff.

## Active Context
<!-- ACTIVE:START -->
- Updated at: `2026-04-17 04:09 +07`
- Branch: `develop`
- Current focus: Use project-safe browser automation and curated skills as the default UI debugging stack
- Last verified workflow status: PASS `bash -n Start_Platform.command scripts/run_unified_platform.sh scripts/run_playwright_cli.sh`, PASS `./scripts/run_playwright_cli.sh --help`, PASS `python3 /Users/anton/.codex/skills/screenshot/scripts/take_screenshot.py --help`, PASS `./scripts/run_playwright_cli.sh open http://127.0.0.1:3000/ --headed`, PASS `cd apps/web && npm run typecheck`
- Biggest operational risk: playwright-interactive is installed, but it still needs a new Codex session with js_repl enabled before it becomes usable as a persistent in-process browser debugger.
<!-- ACTIVE:END -->

## Recent Worklog
<!-- WORKLOG:START -->
### 2026-04-17 04:09 +07 | develop
- Summary: Integrated curated browser automation skills and project-safe Playwright wrapper
- Changed:
  - Installed curated skills: playwright-interactive, screenshot, cli-creator
  - scripts/run_playwright_cli.sh and .gitignore browser artifact/cache rules
  - Russian docs and homepage wording for live UI review workflow
- Verified:
  - PASS `bash -n Start_Platform.command scripts/run_unified_platform.sh scripts/run_playwright_cli.sh`
  - PASS `./scripts/run_playwright_cli.sh --help`
  - PASS `python3 /Users/anton/.codex/skills/screenshot/scripts/take_screenshot.py --help`
  - PASS `./scripts/run_playwright_cli.sh open http://127.0.0.1:3000/ --headed`
  - PASS `cd apps/web && npm run typecheck`
- Risk:
  - playwright-interactive is installed, but it still needs a new Codex session with js_repl enabled before it becomes usable as a persistent in-process browser debugger.
### 2026-04-17 03:46 +07 | develop
- Summary: Clarified and hardened Start_Platform desktop launcher semantics
- Changed:
  - Start_Platform.command detach path and canonical wrapper behavior
  - docs/ru/code-map.md launcher documentation
- Verified:
  - PASS `bash -n Start_Platform.command scripts/run_unified_platform.sh`
  - PASS `./Start_Platform.command --help`
- Risk:
  - Start_Platform.command is still a convenience launcher; canonical automation and docs should continue to target scripts/run_unified_platform.sh.
### 2026-04-17 03:33 +07 | develop
- Summary: Added live project visual map and enabled recurring repo/platform/map automations
- Changed:
  - apps/web/project-map route and visual map loader
  - scripts/update_project_visual_map.py and generated docs/ru/visuals outputs
  - Hourly Repo Guard, Hourly Platform Smoke, Hourly Visual Map, Weekly Release Gate automations
- Verified:
  - PASS `cd apps/web && npm run typecheck`
  - PASS `cd apps/web && npm run build`
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Automations now exist in Codex, but their long-run value still depends on the project continuing to record true state in .codex/project-memory.md and docs/ru.
### 2026-04-17 03:10 +07 | develop
- Summary: Ran project skill smoke audit and hardened unified platform watch mode
- Changed:
  - scripts/run_unified_platform.sh
  - docs/ru/code-map.md
- Verified:
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - Current skill execution is procedural: event-driven skills like ci-watch-fix and donor-boundary-audit still need a real failing CI or explicit donor task to be meaningfully exercised.
### 2026-04-17 03:01 +07 | develop
- Summary: Activated project skills via CODEX_HOME symlinks and normalized skill metadata
- Changed:
  - scripts/install_project_skills.sh
  - skills/audit-docs-vs-runtime/SKILL.md
  - skills/git-safe-commit/SKILL.md
  - skills/operate-platform/SKILL.md
  - skills/operate-standalone-intelligence/SKILL.md
  - docs/ru/README.md
  - scripts/verify_workflow.sh
- Verified:
  - PASS `bash scripts/install_project_skills.sh`
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - The current live Codex session still needs a restart before newly linked skills appear in the runtime-discovered skill list.
### 2026-04-17 02:57 +07 | develop
- Summary: Added project skills for regression, CI, verification, release gating, docs sync, skill scanning, and donor boundary audit
- Changed:
  - skills/web-regression-pass/SKILL.md
  - skills/ci-watch-fix/SKILL.md
  - skills/verify-implementation/SKILL.md
  - skills/release-readiness-gate/SKILL.md
  - skills/docs-sync-curator/SKILL.md
  - skills/skill-pattern-scan/SKILL.md
  - skills/donor-boundary-audit/SKILL.md
  - docs/ru/README.md
  - docs/ru/code-map.md
- Verified:
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - Existing older local skills still use the previous plain markdown format; the new skills already use explicit name/description frontmatter.
### 2026-04-17 02:47 +07 | develop
- Summary: Enforced Russian comment guard and completed hard repo workflow audit
- Changed:
  - src/magon_standalone/russian_comment_contract.py
  - scripts/check_russian_comment_contract.py
  - tests/test_russian_comment_contract.py
  - .githooks/pre-commit
  - scripts/verify_workflow.sh
  - AGENTS.md
  - docs/repo-workflow.md
  - docs/ru/README.md
  - docs/ru/repo-workflow.md
  - docs/ru/code-map.md
- Verified:
  - PASS `./.venv/bin/python -m unittest tests.test_russian_comment_contract`
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Russian comment quality is now enforced by RU markers, but semantic usefulness still depends on disciplined review.
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
