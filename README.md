# MagonOS Standalone

Standalone MagonOS platform.

This repository is now the primary platform-of-record.
The legacy donor repo at `/Users/anton/Desktop/MagonOS/MagonOS` remains a donor / bridge / legacy-shell repository only.

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
- donor ORM/models/views
- donor admin UI
- accounting / invoice / payment ERP ownership
- full donor CRM / ERP replacement

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
- `gpt_doc/platform_architecture_report_ru.docx`
- `gpt_doc/platform_documentation_pack_ru.docx`

The intended wave1 runtime is the new stack itself. Any mounted legacy standalone contour should be treated only as a temporary compatibility bridge during transition.

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

Legacy bridge is opt-in only:

```bash
MAGON_FOUNDATION_LEGACY_ENABLED=true ./scripts/run_foundation_unified.sh --fresh
```

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

## Legacy compatibility start
```bash
cd /Users/anton/Desktop/MagonOS-Standalone
./scripts/run_platform.sh --fresh --port 8091
```

## Legacy compatibility all-in-one start
One command starts:
- public Next.js shell on `http://127.0.0.1:3000/`
- operator/runtime surfaces under the same shell at `/ops`, `/ui/...`
- standalone backend on `http://127.0.0.1:8091/`

```bash
cd /Users/anton/Desktop/MagonOS-Standalone
./scripts/run_unified_platform.sh --fresh
```

## Production/deploy start
```bash
cd /Users/anton/Desktop/MagonOS-Standalone
PORT=8091 ./scripts/run_deploy.sh
```

Optional staging bootstrap from fixture:
```bash
MAGON_STANDALONE_BOOTSTRAP_FIXTURE=tests/fixtures/vn_suppliers_raw.json PORT=8091 ./scripts/run_deploy.sh
```

## Local URLs
- public shell: http://127.0.0.1:3000/
- foundation login: http://127.0.0.1:3000/login

Direct backend URLs still exist for debugging:
- http://127.0.0.1:8091/

Legacy compatibility surfaces exist only when `MAGON_FOUNDATION_LEGACY_ENABLED=true`:
- http://127.0.0.1:3000/dashboard
- http://127.0.0.1:3000/ops-workbench
- http://127.0.0.1:3000/ops
- http://127.0.0.1:3000/ui/companies
- http://127.0.0.1:3000/ui/commercial-pipeline
- http://127.0.0.1:3000/ui/quote-intents
- http://127.0.0.1:3000/ui/production-handoffs
- http://127.0.0.1:3000/ui/production-board
- http://127.0.0.1:3000/ui/review-queue
- http://127.0.0.1:3000/ui/feedback-status
- http://127.0.0.1:3000/ui/feedback-events
- http://127.0.0.1:8091/ui/companies

## Core API endpoints
- `GET /health`
- `GET /status`
- `GET /raw-records`
- `GET /companies`
- `GET /scores`
- `GET /dedup-decisions`
- `GET /review-queue`
- `GET /feedback-events`
- `GET /feedback-status`
- `GET /feedback-status/{source_key}`
- `POST /runs`
- `POST /feedback-events`

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
- Auto-synced at: `2026-04-18 06:10 +07`
- Current focus: Make the standalone runtime and smoke contour prove the same PostgreSQL-first business flow that the launcher and operator demos use.
- Last verified workflow status: PASS `./.venv/bin/python -m unittest tests.test_foundation_seed_repeatable`, PASS `./scripts/run_foundation_migrations.sh && ./.venv/bin/python scripts/seed_foundation.py`, PASS `bash ./scripts/foundation_order_smoke_check.sh`, PASS `./scripts/verify_workflow.sh --with-web`
- Biggest operational risk: Fast unit tests still mix SQLite-backed isolation with the live PostgreSQL-first runtime, so DB parity is much better now but not yet absolute across the entire test suite.
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
  - embedded entity/dependency reference: `http://127.0.0.1:3000/reference`
  - public marketing layer: `http://127.0.0.1:3000/marketing`
  - public showcase: `http://127.0.0.1:3000/catalog`
  - public catalog detail: `http://127.0.0.1:3000/catalog/{itemCode}`
  - public RFQ entry: `http://127.0.0.1:3000/rfq`
  - public draft editor: `http://127.0.0.1:3000/drafts/{draftCode}`
  - public request view: `http://127.0.0.1:3000/requests/{customerRef}`
  - public request offer compare: `http://127.0.0.1:3000/requests/{customerRef}` (compare block on the same page)
  - foundation login: `http://127.0.0.1:3000/login`
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
  - operator LLM status/test surface: `http://127.0.0.1:8091/api/v1/operator/llm/status`
  - direct backend debug: `http://127.0.0.1:8091/`
  - compatibility-only legacy surfaces when `MAGON_FOUNDATION_LEGACY_ENABLED=true`:
  - `http://127.0.0.1:3000/ops-workbench`
  - `http://127.0.0.1:3000/ops`
  - `http://127.0.0.1:3000/ui/*`
<!-- AUTO-SYNC:README:END -->

## Deploy notes
- This repo is the official product runtime.
- The donor repo is no longer the official startup path.
- `scripts/run_platform.sh` is legacy compatibility-only.
- `scripts/run_unified_platform.sh` is legacy compatibility-only.
- `scripts/run_deploy.sh` is the deploy/runtime entrypoint.
- `Procfile` points at the production entrypoint.
- The app is independent from the donor runtime.
- Legacy standalone contour may still exist as a temporary compatibility surface, but it is opt-in.
- Foundation wave1 skeleton is the forward runtime base and is already running on the target stack through PostgreSQL + Redis + Alembic + Docker Compose.
