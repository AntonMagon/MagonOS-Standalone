# MagonOS Standalone

Standalone MagonOS platform.

This repository is now the primary platform-of-record.
The legacy Odoo repo at `/Users/anton/Desktop/MagonOS/MagonOS` remains a donor / bridge / legacy-shell repository only.

Included:
- supplier discovery pipeline
- fixture-backed standalone runtime
- standalone SQLite persistence
- standalone HTTP API
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
- Odoo ORM/models/views
- Odoo admin UI
- accounting / invoice / payment ERP ownership
- full Odoo CRM / ERP replacement

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

## Local platform start
```bash
cd /Users/anton/Desktop/MagonOS-Standalone
./scripts/run_platform.sh --fresh --port 8091
```

## Unified platform start
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
- platform dashboard: http://127.0.0.1:3000/dashboard
- ops workspace: http://127.0.0.1:3000/ops-workbench
- operator console: http://127.0.0.1:3000/ops
- company workbench: http://127.0.0.1:3000/ui/companies
- commercial pipeline: http://127.0.0.1:3000/ui/commercial-pipeline
- quote intents: http://127.0.0.1:3000/ui/quote-intents
- production handoffs: http://127.0.0.1:3000/ui/production-handoffs
- production board: http://127.0.0.1:3000/ui/production-board
- review queue: http://127.0.0.1:3000/ui/review-queue
- feedback status: http://127.0.0.1:3000/ui/feedback-status
- feedback audit: http://127.0.0.1:3000/ui/feedback-events

Direct backend URLs still exist for debugging:
- http://127.0.0.1:8091/
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
- Auto-synced at: `2026-04-17 05:58 +07`
- Current focus: Stable autosync, staggered automation cadence, and a verified path to promote develop to main
- Last verified workflow status: PASS `./.venv/bin/python -m unittest tests.test_periodic_checks tests.test_launchd_periodic_checks tests.test_observability tests.test_repo_autosync`, PASS `./scripts/verify_workflow.sh --with-web`, PASS `./.venv/bin/python scripts/run_periodic_checks.py --mode manual`
- Biggest operational risk: Local dev-shell latency under k6 load is still the main unresolved production-scale risk; the new cadence only removes automation overlap and drift noise.
- Validated contour:
  - company
  - commercial/customer context
  - opportunity
  - quote intent / RFQ boundary
  - production handoff
  - production board
- Standalone-owned capabilities:
  - supplier intelligence pipeline
  - normalization / enrichment / dedup / scoring
  - review queue
  - routing / qualification decisions
  - feedback ledger / projection
  - workforce estimation
- Active repo automations:
  - Platform Smoke 2h
  - Repo Guard 3h
  - Visual Map 6h
  - Weekly Release Gate
- Runtime surfaces:
  - public shell: `http://127.0.0.1:3000/`
  - dashboard: `http://127.0.0.1:3000/dashboard`
  - ops workbench: `http://127.0.0.1:3000/ops-workbench`
  - operator console: `http://127.0.0.1:3000/ops`
  - operator pages: `http://127.0.0.1:3000/ui/*`
  - direct backend debug: `http://127.0.0.1:8091/`
<!-- AUTO-SYNC:README:END -->

## Deploy notes
- This repo is the official product runtime.
- The source Odoo repo is no longer the official startup path.
- `scripts/run_platform.sh` is for local product use.
- `scripts/run_unified_platform.sh` is the official local all-in-one startup path.
- `scripts/run_deploy.sh` is the deploy/runtime entrypoint.
- `Procfile` points at the production entrypoint.
- The app is independent from Odoo runtime.
- SQLite is still the production constraint; this setup is fine for one-node deployment, staging, and internal use.
