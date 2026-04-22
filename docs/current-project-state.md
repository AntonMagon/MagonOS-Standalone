# Current Project State

## Canonical repo roles
- Active product repo: `/Users/anton/Desktop/MagonOS-Standalone`
- Historical source repo for evidence-only inspection: `/Users/anton/Desktop/MagonOS/MagonOS`

## Planning truth
- Wave1 implementation source-of-truth: `gpt_doc/codex_wave1_spec_ru.docx`
- Read-only export of the same planning spec: `gpt_doc/codex_wave1_spec_ru.pdf`
- Expanded product/planning canon for the current standalone shaping also includes:
  - `gpt_doc/platform_documentation_pack_ru_v3.docx`
  - `gpt_doc/platform_documentation_pack_ru_with_marketing.docx`
  - `gpt_doc/project_marketing_research_vietnam_ru.docx`
- This file remains the runtime/verification truth, but product-facing UX, IA, marketing copy, and role surfaces must now be checked against that expanded `gpt_doc` package instead of reading the raw wave1 spec in isolation.

## Runtime truth
- Standalone is the primary platform-of-record.
- The historical source repo is evidence-only and is not part of the active runtime.
- Default work happens only in the standalone repo.
- The historical source repo is read-only unless the task explicitly requires evidence inspection or boundary work.
- Foundation wave1 target runtime is the new FastAPI modular-monolith stack on PostgreSQL/Redis/Celery/Caddy/Compose.
- Wave1 runtime truth is the active foundation contour only; old compatibility shells are not part of the current execution model.

## Verified stack baseline
- web runtime: `Node v22.22.2`
- web package manager: `npm 10.9.7`
- web app layer: `Next 15.5.15`, `React 19.2.5`, `React DOM 19.2.5`
- api/core runtime: `Python 3.10.20`
- api/core packages: `FastAPI 0.136.0`, `SQLAlchemy 2.0.49`, `Alembic 1.18.4`, `Celery 5.6.3`, `redis-py 7.4.0`, `psycopg 3.3.3`, `uvicorn 0.44.0`, `sentry-sdk 2.58.0`
- infra images: `PostgreSQL 16.13`, `Redis 7.4.8`, `Caddy 2.8.4`
- Update policy: no forced stack upgrade is required right now because the verified contour is internally consistent and green on the live compose runtime. Prefer controlled upgrades only when a concrete compatibility/security/runtime need appears.

## Resource baseline
- Current Colima profile: `2 CPU / 2 GB RAM / 20 GB disk`
- Verified steady-state compose usage is roughly `430-450 MiB` total across `api + worker + web + db + redis + caddy`
- Current runtime therefore has about `1.4 GiB` free headroom inside the VM
- Recommended sizing:
  - `2 GB`: normal local runtime, smoke checks, login/health verification, routine rebuilds
  - `3 GB`: concurrent rebuilds plus browser-heavy local work on the same host
  - `4 GB`: Playwright/browser automation, extra services, or materially heavier frontend builds
  - `6 GB`: not needed for the current wave1 contour

## Validated standalone contour
- company
- request draft / intake boundary
- commercial/customer context
- opportunity
- quote intent / RFQ boundary
- production handoff
- production board

Also already standalone-owned:
- company/supplier/site registry contour with raw -> normalized -> confirmed layering
- supplier intelligence pipeline
- supplier source registry with both repeatable fixture ingest and selectable live parsing ingest over the existing supplier-intelligence discovery layer
- operator source control with adapter health, latest ingest outcome, queued parsing runs, retry, and force-rerun actions directly from the standalone UI
- env-gated LLM connection for `ai_assisted` supplier extraction fallback with explicit operator status/test path instead of a hidden black-box runtime
- repo-aware periodic supplier scheduler for live parsing/classification; fixture source stays manual-only while `scenario_live` can be enqueued continuously on a launchd cadence
- normalization / enrichment / dedup / scoring
- lightweight marketing/conversion layer over showcase + RFQ + guest draft entry
- limited catalog / showcase contour with guest draft + RFQ entry
- draft autosave / abandoned / archive-ready intake layer
- central request review queue with blocker/clarification flow
- request draft -> request submit flow with required-field gating
- versioned offer layer with compare, confirmation reset, accept/decline/expire, and separate order conversion
- order layer with `OrderLine`, internal payment skeleton, ledger trail, and operator workbench
- managed files/documents contour with storage abstraction, versioning, checks, templates, and role-based download flow
- admin configuration contour for reason codes, rules, rule versions, notification rules, and supplier source settings through API/UI instead of seed-only edits
- foundation FastAPI skeleton with separate draft/request/offer/order entities
- routing / qualification decisions
- feedback ledger / projection
- workforce estimation

## Current dangerous overlap
The main unresolved overlap is commercial semantics around:
- customer/account identity
- opportunity/lead ownership
- RFQ / quote boundary

Do not pretend full CRM/quote parity exists.

## Still out of scope by default
- accounting
- invoice / payment
- full ERP order management
- giant generic CRM
- broad legacy entity mirroring
- source repo feature growth

## Canonical commands
- foundation backend:
  - `./.venv/bin/python scripts/run_foundation_api.py --host 127.0.0.1 --port 8091`
- unified foundation local-up:
  - `./scripts/run_foundation_unified.sh --fresh`
  - local launcher/unified path now auto-starts `db + redis` through `docker compose`/`colima` before migrations and backend/web boot
- desktop launcher for the same local contour:
  - `./Start_Platform.command`
  - `./Start_Platform.command --detach --no-open --keep-db --no-seed`
  - detached mode now uses the repo-local double-fork helper `scripts/run_detached_command.py`, so backend/web must remain alive after the launcher shell exits instead of depending on the parent terminal session
- hourly self-heal watchdog for the launcher:
  - `./scripts/install_launchd_launcher_watchdog.sh --interval 3600`
  - `./scripts/launchd_launcher_watchdog_status.sh`
- hourly supplier parser/classifier scheduler:
  - `./scripts/install_launchd_supplier_scheduler.sh --interval 3600`
  - `./scripts/launchd_supplier_scheduler_status.sh`
  - `./.venv/bin/python scripts/run_supplier_scheduler.py`
- perf smoke/load/stress:
  - `./scripts/run_perf_suite.sh smoke`
  - `./scripts/run_perf_suite.sh load`
  - `./scripts/run_perf_suite.sh stress`
  - perf warmup and k6 probes must use the live foundation URLs (`/health/live`, `/health/ready`, `/api/v1/meta/system-mode`, `/api/v1/public/catalog/items`, `/login`, `/marketing`, `/request-workbench`, `/orders`, `/suppliers`) instead of removed legacy surfaces like `/status` or `/ui/*`
- foundation migrate + seed:
  - `./scripts/run_foundation_migrations.sh`
  - `./.venv/bin/python scripts/seed_foundation.py`
  - migrations now assume the same local PostgreSQL contour as launcher/unified instead of a separate SQLite dev truth
  - repeatable `seed_foundation.py` on the local PostgreSQL runtime is now part of the verified path; rerunning migrate + seed must not abort on special scopes like `users:USR` or `request_customer_refs`
  - all foundation smoke scripts now also run on isolated temporary PostgreSQL databases instead of temporary SQLite files
  - blank `MAGON_FOUNDATION_REDIS_URL` in test/smoke and CI is now treated as an explicit Redis disable signal instead of silently falling back to `redis://127.0.0.1:6379/0`
- supplier demo pipeline:
  - `./.venv/bin/python scripts/run_supplier_demo_pipeline.py --source-code SRC-00001 --idempotency-key demo-suppliers-001`
- fixture pipeline:
  - `./.venv/bin/python scripts/run_pipeline.py --fixture tests/fixtures/vn_suppliers_raw.json`
- backend verification:
  - `./.venv/bin/python -m unittest tests.test_persistence tests.test_api tests.test_operations`
- foundation verification:
  - `./scripts/verify_workflow.sh` now falls back to `python3`/`python` when the repo venv is absent, so GitHub Actions can execute the same verification contract
  - `./.venv/bin/python -m unittest tests.test_foundation_api`
  - `./.venv/bin/python -m unittest tests.test_foundation_suppliers`
  - `./.venv/bin/python -m unittest tests.test_foundation_catalog`
  - `./.venv/bin/python -m unittest tests.test_foundation_draft_request`
  - `./.venv/bin/python -m unittest tests.test_foundation_offers`
  - `./.venv/bin/python -m unittest tests.test_foundation_orders`
  - `./.venv/bin/python -m unittest tests.test_foundation_files_documents`
  - `./scripts/foundation_smoke_check.sh`
  - `./scripts/foundation_supplier_smoke_check.sh`
  - `./scripts/foundation_catalog_smoke_check.sh`
  - `./scripts/foundation_request_smoke_check.sh`
  - `./scripts/foundation_offer_smoke_check.sh`
  - `./scripts/foundation_order_smoke_check.sh`
  - `./scripts/foundation_files_documents_smoke_check.sh`
  - `./scripts/foundation_messages_dashboards_smoke_check.sh`
  - the canonical `./scripts/verify_workflow.sh` path now executes the foundation smoke scripts above on temporary PostgreSQL databases instead of treating them as optional manual-only checks
- web typecheck when web code changed:
  - `cd apps/web && npm run typecheck`

## Browser automation rule
- Project browser automation is Chrome-only.
- Use `./scripts/run_playwright_cli.sh` only with Google Chrome.
- Chrome pinning applies only to browser-driven commands; meta-commands like `list`, `close-all`, and `kill-all` must stay usable without an injected `--browser` flag.
- Do not start Firefox, WebKit, or alternate Playwright browser runtimes for this repo.
- If old Playwright browser caches exist, they should be removed instead of reused.

## Runtime surfaces
- public shell: `http://127.0.0.1:3000/`
- embedded entity/dependency reference: `http://127.0.0.1:3000/reference`
- public marketing layer: `http://127.0.0.1:3000/marketing`
- public showcase: `http://127.0.0.1:3000/catalog`
- public catalog detail: `http://127.0.0.1:3000/catalog/{itemCode}`
- public RFQ entry: `http://127.0.0.1:3000/rfq`
- public draft editor: `http://127.0.0.1:3000/drafts/{draftCode}`
- public request view: `http://127.0.0.1:3000/requests/{customerRef}`
- public request offer compare: `http://127.0.0.1:3000/requests/{customerRef}` (compare block on the same page)
- foundation login: `http://127.0.0.1:3000/login`
- admin configuration: `http://127.0.0.1:3000/admin-config`
- operator request workbench: `http://127.0.0.1:3000/request-workbench`
- operator request detail: `http://127.0.0.1:3000/request-workbench/{requestCode}`
- operator offer compare / revision: `http://127.0.0.1:3000/request-workbench/{requestCode}` (commercial block on the same page)
- managed request files/documents: `http://127.0.0.1:3000/request-workbench/{requestCode}` and `http://127.0.0.1:3000/requests/{customerRef}`
- operator order workbench: `http://127.0.0.1:3000/orders`
- operator order detail: `http://127.0.0.1:3000/orders/{orderCode}`
- managed order files/documents: `http://127.0.0.1:3000/orders/{orderCode}`
- supplier workbench: `http://127.0.0.1:3000/suppliers`
- supplier workbench now acts as the operator console for source adapters: health, latest success/failure, queued ingest visibility, retry, and force-rerun live there instead of a hidden API-only path
- supplier site card: `http://127.0.0.1:3000/supplier-sites/{siteCode}`
- supplier raw ingest: `http://127.0.0.1:3000/supplier-ingests/{ingestCode}`
- supplier raw ingest detail now shows explainable async state (`queued/running/failed/completed`, task id, trigger mode, retry history, failure detail) and exposes retry / rerun actions
- supplier source API now also exposes schedule/classification state so operator tooling can tell which source runs continuously, when the next due window arrives, and whether LLM-assisted fallback is enabled
- admin configuration UI/API now owns baseline business settings for wave1, so reason catalogs, workflow rules, notification rules, and supplier source schedule/classification no longer require code edits
- operator LLM status/test surface: `http://127.0.0.1:8091/api/v1/operator/llm/status`
- direct backend debug: `http://127.0.0.1:8091/`
## Reference surface
- Fast shell entry: `/reference`
- Russian repo doc: `docs/ru/platform-entity-reference.md`
- Use this when you need a quick answer to:
  - which entity owns a given stage;
  - which screen should be used for it;
  - which dependency boundary must remain explicit.

## Working rules
- Trust code, tests, and runtime over stale docs.
- Do not hallucinate missing business logic.
- Do not widen feedback into generic sync.
- Do not spend runs on README/wrapper cleanup unless explicitly asked.
- Verify with the smallest command that proves the result.

## CI parity note
- Foundation smoke and migration scripts must work both with repo `.venv` and with a clean CI runner Python.
- If a smoke script requires `./.venv/bin/python` unconditionally, treat it as repo drift because GitHub Actions may only have `python3`.

## GitHub branch truth
- Default GitHub branch is `main`.
- Protected checks for the primary branches must use the live workflow names:
  - `foundation-quality`
  - `foundation-smoke`
  - `web-quality`
- Stale branch protection names like `python-tests`, `smoke-runtime`, and `web-build` are invalid drift and must be removed.
