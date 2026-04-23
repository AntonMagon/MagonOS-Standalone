# MagonOS Standalone

Standalone MagonOS platform.

This repository is now the primary platform-of-record.
The historical source repo at `/Users/anton/Desktop/MagonOS/MagonOS` is inspection-only and is not part of the active runtime.

Included:
- supplier discovery pipeline
- fixture-backed standalone runtime
- standalone PostgreSQL persistence
- standalone HTTP API
- foundation FastAPI modular-monolith skeleton
- operator console
- unified public web shell (`apps/web`)
- narrow downstream feedback ingestion
- company workbench
- review queue and operator decision flow
- commercial pipeline / commercial preparation state
- quote intents
- production handoffs
- production board

Not included:
- historical source ORM/models/views
- historical source admin UI
- accounting / invoice / payment ERP ownership
- full external CRM / ERP replacement

## Wave1 foundation
Foundation skeleton for the first Codex wave now lives in the same repo and adds:

- FastAPI modular monolith
- Alembic migrations
- PostgreSQL/Redis/Celery/Caddy compose skeleton
- minimal auth/authz with roles `guest / customer / operator / admin`
- audit / health / telemetry baseline
- separate entities for `draft_request / request / offer / order`

Planning source-of-truth for this contour:
- `gpt_doc/codex_wave1_spec_ru.docx`

The intended wave1 runtime is the active foundation stack itself.

Quick path:

```bash
./scripts/run_foundation_migrations.sh
./.venv/bin/python scripts/seed_foundation.py
./.venv/bin/python scripts/run_foundation_api.py --host 127.0.0.1 --port 8091
```

Unified local path:

```bash
./scripts/run_foundation_unified.sh --fresh
```

This path now auto-starts local `db + redis` through `docker compose`/`colima` and keeps the active local runtime on PostgreSQL instead of a separate SQLite fallback.

Runbook:

- Russian runbook: `docs/ru/foundation-runbook.md`
- Implementation log: `docs/implementation-log-wave1-foundation.md`

## Setup
```bash
cd /Users/anton/Desktop/MagonOS-Standalone
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e .
# Optional only if you want live crawling instead of fixture mode:
pip install -e .[live]
```

## Production/deploy start
```bash
cd /Users/anton/Desktop/MagonOS-Standalone
cp .env.prod.example .env.prod
# replace placeholder passwords in .env.prod first
./scripts/run_deploy.sh
```

Useful deploy helpers:
```bash
./scripts/run_deploy.sh status
./scripts/run_deploy.sh logs --follow api web
./scripts/run_deploy.sh restart --build api web worker
./scripts/run_deploy.sh down
```

## Local URLs
- public shell: http://127.0.0.1:3000/
- foundation login: http://127.0.0.1:3000/login
- admin config: http://127.0.0.1:3000/admin-config
- admin dashboard: http://127.0.0.1:3000/admin-dashboard
- supplier workbench: http://127.0.0.1:3000/suppliers
- request workbench: http://127.0.0.1:3000/request-workbench
- orders: http://127.0.0.1:3000/orders

Direct backend URLs still exist for debugging:
- http://127.0.0.1:8091/

## Core API endpoints
- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/meta/system-mode`
- `GET /api/v1/public/catalog/items`
- `GET /api/v1/operator/reason-codes`
- `GET /api/v1/operator/rules`
- `POST /api/v1/admin/reason-codes`
- `PATCH /api/v1/admin/reason-codes/{reasonCode}`
- `POST /api/v1/admin/rules`
- `PATCH /api/v1/admin/rules/{ruleCode}`
- `POST /api/v1/admin/rules/{ruleCode}/versions`
- `GET /api/v1/admin/notification-rules`
- `POST /api/v1/admin/notification-rules`
- `PATCH /api/v1/admin/notification-rules/{notificationRuleCode}`
- `GET /api/v1/operator/supplier-sources`
- `PATCH /api/v1/admin/supplier-sources/{sourceRegistryCode}`
- `GET /api/v1/operator/llm/status`

## Local CLI helpers
```bash
./.venv/bin/python scripts/run_pipeline.py --fixture tests/fixtures/vn_suppliers_raw.json
./.venv/bin/python scripts/inspect_results.py --table companies
./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## Required Repo Workflow
This repo now keeps its working context and close-out discipline inside the repository itself.

Required entrypoints:

```bash
./scripts/restore_context.sh
./scripts/install_repo_guards.sh
./scripts/verify_workflow.sh
./.venv/bin/python scripts/finalize_task.py --summary "..." --changed "..." --verify "./scripts/verify_workflow.sh"
```

Canonical rules:
- start substantial work with `./scripts/restore_context.sh`
- install versioned git guards with `./scripts/install_repo_guards.sh`
- update `.codex/project-memory.md` before committing substantial repo changes
- do not claim GitHub visibility until `git push` actually succeeds

Detailed workflow: `docs/repo-workflow.md`

## Auto-synced operating status
<!-- AUTO-SYNC:README:START -->
- Auto-synced at: `2026-04-23 15:01 +07`
- Current focus: Keep the local automation layer truthful and launchd-stable on top of the active foundation runtime.
- Last verified workflow status: PASS `./scripts/launchd_launcher_watchdog_status.sh >/tmp/magon-launcher-watchdog-status.txt`, PASS `./scripts/launchd_periodic_checks_status.sh >/tmp/magon-periodic-checks-status.txt`, PASS `./.venv/bin/python scripts/check_russian_locale_integrity.py --web-url http://127.0.0.1:3000`, PASS `./.venv/bin/python -m unittest tests.test_launchd_launcher_watchdog tests.test_launchd_periodic_checks`
- Biggest operational risk: Repo launchd automation is now green on this Mac, but the user-level ~/.codex/automations state remains machine-local and is not propagated by a repo push alone.
- Validated contour:
  - company
  - request draft / intake boundary
  - commercial/customer context
  - opportunity
  - quote intent / RFQ boundary
  - production handoff
  - production board
- Standalone-owned capabilities:
  - company/supplier/site registry contour with raw -> normalized -> confirmed layering
  - supplier intelligence pipeline
  - scenario-driven live parsing now distinguishes static directories, rendered directories, plain company sites, and JS-heavy company sites; supplier-owned sites flagged as browser-required must route through a browser-aware company-site executor instead of the old requests-only path
  - supplier source registry with both repeatable fixture ingest and selectable live parsing ingest over the existing supplier-intelligence discovery layer
  - operator source control with adapter health, latest ingest outcome, queued parsing runs, retry, and force-rerun actions directly from the standalone UI
  - env-gated LLM connection for `ai_assisted` supplier extraction fallback with explicit operator status/test path instead of a hidden black-box runtime
  - repo-aware periodic supplier scheduler for live parsing/classification; fixture source stays manual-only while `scenario_live` can be enqueued continuously on a launchd cadence
  - normalization / enrichment / dedup / scoring
  - lightweight marketing/conversion layer over showcase + RFQ + guest draft entry
  - limited catalog / showcase contour with guest draft + RFQ entry
  - product-first public shell over `/`, `/marketing`, `/catalog`, and `/rfq` with managed-service copy instead of architecture jargon
  - draft autosave / abandoned / archive-ready intake layer
  - central request review queue with blocker/clarification flow
  - request draft -> request submit flow with required-field gating
  - versioned offer layer with compare, confirmation reset, accept/decline/expire, and separate order conversion
  - order layer with `OrderLine`, internal payment skeleton, ledger trail, and operator workbench
  - managed files/documents contour with storage abstraction, versioning, checks, templates, and role-based download flow
  - admin configuration contour for reason codes, rules, rule versions, notification rules, and supplier source settings through API/UI instead of seed-only edits
  - session-driven operator/admin screens now read one stable foundation-session snapshot through `useFoundationSession()`, so logged-in routes do not flash the guest gate or hit hydration mismatches after localStorage boot
  - foundation FastAPI skeleton with separate draft/request/offer/order entities
  - routing / qualification decisions
  - feedback ledger / projection
  - workforce estimation
- Active repo automations:
  - Architecture Drift Watch
  - Daily Project Digest
  - Dev Review Pulse
  - Platform Smoke 2h
  - Repo Guard 3h
  - Visual Map Daily
  - Nightly Deep Review
  - Operator Flow Audit
  - PR Branch Hygiene
  - RU Locale Guard 6h
  - Weekly Release Gate
- Runtime surfaces:
  - public shell: `http://127.0.0.1:3000/`
  - public shell now runs from the production Next bundle by default; the home/status path must stay on short revalidation instead of permanent `no-store`
  - public shell, marketing, catalog, RFQ, request, order, supplier, and admin pages were rechecked in the browser after the latest product-copy/layout pass; the live shell must stay free of raw technical dumps, split-language UI drift, and hydration mismatch errors
  - measured local timings after the production-web switch:
  - `/` about `0.40s` instead of `~2.60s` on the old `next dev` path
  - `/marketing` about `0.37s` instead of `~0.85s`
  - `/catalog` about `0.06s` instead of `~0.66s`
  - `/request-workbench` about `0.04s` instead of `~0.59s`
  - `/orders` about `0.12s` instead of `~0.37s`
  - warmed detached production shell is now even faster in steady state:
  - `/` about `0.04s`
  - `/marketing` about `0.02s`
  - `/catalog` about `0.01s`
  - `/request-workbench` about `0.01s`
  - `/orders` about `0.01s`
  - `/suppliers` about `0.01s`
  - backend `/health/ready` about `0.01s`
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
  - for admin users the same `/suppliers` surface now also exposes inline operational source controls (`enabled`, schedule on/off, interval, classification mode) so routine parser management no longer requires a second trip to `/admin-config`
  - supplier site card: `http://127.0.0.1:3000/supplier-sites/{siteCode}`
  - supplier raw ingest: `http://127.0.0.1:3000/supplier-ingests/{ingestCode}`
  - supplier raw ingest detail now shows explainable async state (`queued/running/failed/completed`, task id, trigger mode, retry history, failure detail) and exposes retry / rerun actions
  - supplier source API now also exposes schedule/classification state so operator tooling can tell which source runs continuously, when the next due window arrives, and whether LLM-assisted fallback is enabled
  - admin configuration UI/API now owns baseline business settings for wave1, so reason catalogs, workflow rules, notification rules, and supplier source schedule/classification no longer require code edits
  - operator LLM status/test surface: `http://127.0.0.1:8091/api/v1/operator/llm/status`
  - direct backend debug: `http://127.0.0.1:8091/`
<!-- AUTO-SYNC:README:END -->

## Deploy notes
- This repo is the official product runtime.
- Active runtime contract is the standalone foundation contour only.
- The historical source repo is no longer the official startup path.
- `scripts/run_deploy.sh` is the VPS/server deploy entrypoint and now wraps the same foundation `docker compose` contour that already acts as the production-like runtime.
- `Procfile` points at the production entrypoint.
- The app is independent from any old bridge runtime.
- Foundation wave1 skeleton is the forward runtime base and is already running on the target stack through PostgreSQL + Redis + Alembic + Docker Compose.
