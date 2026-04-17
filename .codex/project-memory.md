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
- Updated at: `2026-04-17 08:55 +07`
- Branch: `develop`
- Current focus: Keep the Russian docs and shell protected from both English leakage and bad technical hybrid copy.
- Last verified workflow status: PASS `./.venv/bin/python -m unittest tests.test_locale_integrity`, PASS `./scripts/verify_workflow.sh`, PASS `./.venv/bin/python scripts/check_russian_locale_integrity.py --static-only`
- Biggest operational risk: The guard now catches known English leaks and bad hybrid phrases, but it still cannot judge whether a sentence sounds commercially good without manual review.
<!-- ACTIVE:END -->

## Recent Worklog
<!-- WORKLOG:START -->
### 2026-04-17 08:55 +07 | develop
- Summary: Extended the Russian locale guard so it also blocks bad hybrid technical copy in the Russian docs and shell layer.
- Changed:
  - src/magon_standalone/locale_integrity.py
  - tests/test_locale_integrity.py
  - docs/ru/code-map.md
- Verified:
  - PASS `./.venv/bin/python -m unittest tests.test_locale_integrity`
  - PASS `./scripts/verify_workflow.sh`
  - PASS `./.venv/bin/python scripts/check_russian_locale_integrity.py --static-only`
- Risk:
  - The guard now catches known English leaks and bad hybrid phrases, but it still cannot judge whether a sentence sounds commercially good without manual review.
### 2026-04-17 08:46 +07 | develop
- Summary: Audited standalone documentation and removed the remaining English drift from the Russian code map.
- Changed:
  - docs/ru/code-map.md
- Verified:
  - PASS `./scripts/restore_context.sh --check`
  - PASS `./.venv/bin/python scripts/sync_operating_docs.py --check`
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - Russian docs are mostly aligned now, but wording quality still depends on continued review whenever new architecture terms land in project memory or shell text.
### 2026-04-17 08:29 +07 | develop
- Summary: Optimized standalone UI checks for a low-memory MacBook by keeping browser inspection manual, single-window, and outside the default verify path.
- Changed:
  - scripts/run_playwright_cli.sh
  - apps/web/components/navigation/site-header.tsx
  - apps/web/components/sections/section-intro.tsx
  - docs/ru/code-map.md
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Manual browser review still depends on an already running local shell and does not prove every interactive path unless we explicitly drive that one session.
### 2026-04-17 07:59 +07 | develop
- Summary: Cleaned standalone web layout and semantic load on the Russian home and project map surfaces.
- Changed:
  - apps/web/app/page.tsx
  - apps/web/app/project-map/page.tsx
  - apps/web/messages/ru.json
  - apps/web/messages/en.json
  - docs/ru/code-map.md
- Verified:
  - PASS `cd apps/web && npm run typecheck`
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Russian shell wording still depends on upstream project-memory summaries, so uncommon new English phrases may still need explicit localization mapping.
### 2026-04-17 07:43 +07 | develop
- Summary: Added automatic Russian locale guard for source-of-truth and live shell routes
- Changed:
  - scripts/check_russian_locale_integrity.py and src/magon_standalone/locale_integrity.py
  - scripts/verify_workflow.sh and scripts/run_periodic_checks.py locale guard integration
  - docs/ru current-state and project-map Russian source cleanup
  - RU Locale Guard Codex automation
- Verified:
  - PASS `./.venv/bin/python scripts/check_russian_locale_integrity.py --static-only`
  - PASS `./.venv/bin/python scripts/check_russian_locale_integrity.py --web-url http://127.0.0.1:3000`
  - PASS `./scripts/verify_workflow.sh --with-web`
  - PASS `./.venv/bin/python scripts/run_periodic_checks.py --mode manual`
- Risk:
  - The guard now blocks known English domain leakage in Russian source/runtime layers, but deeper wording quality is still a product review problem beyond exact forbidden-term checks.
### 2026-04-17 06:50 +07 | develop
- Summary: Stabilized full-project audit runtime across web, perf, and periodic checks
- Changed:
  - apps/web runtime isolation (.next-dev)
  - unified launcher readiness contract
  - perf warmup and periodic liveness probes
- Verified:
  - PASS `./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`
  - PASS `cd apps/web && npm run build`
  - PASS `./scripts/platform_smoke_check.sh`
  - PASS `./scripts/run_perf_suite.sh smoke`
  - PASS `./.venv/bin/python scripts/run_periodic_checks.py --mode manual`
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Cold-start dev-shell latency can still be worse than steady-state performance; perf smoke is now robust but still measures a development runtime, not a production shell.
### 2026-04-17 06:08 +07 | develop
- Summary: Fixed smoke-runtime CI by making run_platform.sh fall back to PATH python when .venv is absent
- Changed:
  - scripts/run_platform.sh
  - docs/ru/code-map.md
- Verified:
  - PASS `bash -n scripts/run_platform.sh`
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - The smoke-runtime CI failure is fixed at the bootstrap layer; the main remaining system risk is still dev-shell latency under heavier k6 load, not runtime startup.
### 2026-04-17 05:58 +07 | develop
- Summary: Added periodic-run overlap lock and staggered Codex automation cadence
- Changed:
  - scripts/run_periodic_checks.py
  - src/magon_standalone/periodic_checks.py
  - tests/test_periodic_checks.py
  - docs/ru/performance-and-observability.md
- Verified:
  - PASS `./.venv/bin/python -m unittest tests.test_periodic_checks tests.test_launchd_periodic_checks tests.test_observability tests.test_repo_autosync`
  - PASS `./scripts/verify_workflow.sh --with-web`
  - PASS `./.venv/bin/python scripts/run_periodic_checks.py --mode manual`
- Risk:
  - Local dev-shell latency under k6 load is still the main unresolved production-scale risk; the new cadence only removes automation overlap and drift noise.
### 2026-04-17 05:43 +07 | develop
- Summary: Stabilized visual map timestamps for periodic checks
- Changed:
  - scripts/update_project_visual_map.py stable generated_at source
  - visual map outputs no longer drift on idle periodic runs
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - The periodic runner now exits cleanly and stops dirtying the repo on idle runs, but the manual k6 load profile still shows heavy latency on the local dev shell at 25 VUs.
### 2026-04-17 05:39 +07 | develop
- Summary: Added perf, launchd, and observability operating layer
- Changed:
  - k6 perf scenarios and launchers
  - launchd periodic runner and status tooling
  - env-gated Sentry prep for backend and Next shell
  - repo automation/watch/task/docs integration for perf and periodic checks
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - The new smoke and periodic layers are green, but the manual load profile at 25 VUs still shows multi-second latency on the local dev shell, which is a real scaling warning rather than a tooling failure.
### 2026-04-17 04:56 +07 | develop
- Summary: Added local file-watch autosync with Watchman and Task
- Changed:
  - src/magon_standalone/repo_autosync.py autosync planner and loop guards
  - scripts/run_repo_autosync.py scripts/install_repo_automation.sh scripts/repo_automation_status.sh repo automation entrypoints
  - Taskfile.yml and .watchmanconfig local automation config
  - scripts/install_repo_guards.sh scripts/verify_workflow.sh automation contract integration
  - tests/test_repo_autosync.py loop-safe autosync coverage
  - docs/ru/README.md docs/ru/repo-workflow.md docs/ru/code-map.md automation documentation
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - The repo now auto-runs sync and verification on file changes, but autosync still stops at repo-native actions and does not replace human commit/push decisions or Codex skill dispatch across chats.
### 2026-04-17 04:35 +07 | develop
- Summary: Synced visual project map with the new operating-doc automation state
- Changed:
  - scripts/update_project_visual_map.py owned-capabilities fallback for English current-state labels
  - docs/ru/visuals/project-map.md docs/ru/visuals/project-map.json regenerated current state
  - docs/visuals/project-map.md docs/visuals/project-map.json regenerated current state
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - The visual map now follows the new operating-doc sync state, but scheduled automations still report drift through inbox items rather than auto-committing repo changes.
### 2026-04-17 04:35 +07 | develop
- Summary: Fixed visual map generator fallback for standalone-owned capabilities and regenerated visual map docs
- Changed:
  - scripts/update_project_visual_map.py docs/visuals/project-map.md docs/visuals/project-map.json docs/ru/visuals/project-map.md docs/ru/visuals/project-map.json
- Verified:
  - PASS `./scripts/verify_workflow.sh`
- Risk:
  - no additional risk recorded
### 2026-04-17 04:33 +07 | develop
- Summary: Completed automatic root-doc sync for AGENTS.md and README.md
- Changed:
  - scripts/sync_operating_docs.py root-doc sync command
  - src/magon_standalone/operating_docs_sync.py payload parsing and AGENTS/README rendering
  - scripts/finalize_task.py scripts/verify_workflow.sh .githooks/pre-commit scripts/restore_context.sh sync enforcement
  - docs/repo-workflow.md docs/ru/README.md docs/ru/repo-workflow.md docs/ru/code-map.md root-doc contract docs
  - tests/test_operating_docs_sync.py sync tests
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - The repo now auto-syncs root operating docs during finalize and scheduled audits, but Codex still does not provide instant event-driven skill execution on every file save across chats.
### 2026-04-17 04:31 +07 | develop
- Summary: Made root operating docs truly auto-synced with project memory and automations
- Changed:
  - scripts/sync_operating_docs.py root-doc sync entrypoint
  - src/magon_standalone/operating_docs_sync.py canonical AGENTS/README renderer
  - scripts/finalize_task.py scripts/verify_workflow.sh .githooks/pre-commit scripts/restore_context.sh sync enforcement
  - AGENTS.md README.md docs/repo-workflow.md docs/ru/README.md docs/ru/repo-workflow.md docs/ru/code-map.md root-doc automation contract
  - tests/test_operating_docs_sync.py sync coverage
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Codex still does not auto-run the right skill on every file save across chats; the strongest available automation path is now finalize, hooks, and scheduled automations.
### 2026-04-17 04:29 +07 | develop
- Summary: Automated root operating-doc sync and tightened repo guard automation
- Changed:
  - scripts/sync_operating_docs.py root-doc generator
  - src/magon_standalone/operating_docs_sync.py sync payload and markers
  - scripts/finalize_task.py scripts/verify_workflow.sh .githooks/pre-commit scripts/restore_context.sh workflow integration
  - AGENTS.md README.md docs/repo-workflow.md docs/ru/* root-doc sync contract
  - tests/test_operating_docs_sync.py automation-safe sync coverage
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Codex still does not provide true per-file event-driven skill execution across chats; the repo is now automated through hooks, finalize, and scheduled automations instead.
### 2026-04-17 04:18 +07 | develop
- Summary: Fixed verify_workflow regression that broke pre-push after browser automation integration
- Changed:
  - scripts/verify_workflow.sh comment placement in bash -n contract
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - The operating model is now stable again, but skill execution in Codex remains prompt-driven or schedule-driven rather than event-driven on every file save.
### 2026-04-17 04:16 +07 | develop
- Summary: Audited automation and skill operating contract and hardened verification for browser automation
- Changed:
  - docs/ru/README.md clarified curated skill activation and js_repl requirement
  - scripts/verify_workflow.sh now syntax-checks scripts/run_playwright_cli.sh
- Verified:
  - PASS `./scripts/verify_workflow.sh --with-web`
- Risk:
  - Skills and cron automations are active, but Codex still does not provide event-driven per-file auto-skill triggering across chats; only hooks, scheduled automations, and explicit agent invocation are automatic.
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
