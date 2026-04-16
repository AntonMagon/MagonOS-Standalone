# Current Project State

## Canonical repo roles
- Active product repo: `/Users/anton/Desktop/MagonOS-Standalone`
- Legacy donor / bridge repo: `/Users/anton/Desktop/MagonOS/MagonOS`

## Runtime truth
- Standalone is the primary platform-of-record.
- Odoo is donor/bridge only, not the future runtime.
- Default work happens only in the standalone repo.
- Source repo is read-only unless the task explicitly requires donor inspection or boundary work.

## Validated standalone contour
- company
- commercial/customer context
- opportunity
- quote intent / RFQ boundary
- production handoff
- production board

Also already standalone-owned:
- supplier intelligence pipeline
- normalization / enrichment / dedup / scoring
- review queue
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
- broad Odoo entity mirroring
- source repo feature growth

## Canonical commands
- unified platform:
  - `./scripts/run_unified_platform.sh --fresh`
- backend only:
  - `./scripts/run_platform.sh --fresh --port 8091`
- fixture pipeline:
  - `./.venv/bin/python scripts/run_pipeline.py --fixture tests/fixtures/vn_suppliers_raw.json`
- backend verification:
  - `./.venv/bin/python -m unittest tests.test_persistence tests.test_api tests.test_operations`
- web typecheck when web code changed:
  - `cd apps/web && npm run typecheck`

## Runtime surfaces
- public shell: `http://127.0.0.1:3000/`
- dashboard: `http://127.0.0.1:3000/dashboard`
- ops workbench: `http://127.0.0.1:3000/ops-workbench`
- operator console: `http://127.0.0.1:3000/ops`
- operator pages: `http://127.0.0.1:3000/ui/*`
- direct backend debug: `http://127.0.0.1:8091/`

## Working rules
- Trust code, tests, and runtime over stale docs.
- Do not hallucinate missing business logic.
- Do not widen feedback into generic sync.
- Do not spend runs on README/wrapper cleanup unless explicitly asked.
- Verify with the smallest command that proves the result.
