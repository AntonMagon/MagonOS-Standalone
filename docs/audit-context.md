# MagonOS Audit Context

> Historical note:
> this file survives from the donor-extraction phase.
> Current runtime truth must be taken from `docs/current-project-state.md` and `docs/ru/current-project-state.md`.
> Use this file as boundary/audit context only.

## Purpose
This document is the current project context pack for:
- technical due diligence
- business/process audit
- product scope review
- migration/replacement planning

It is intentionally grounded in repository reality, not in aspirational architecture.

## Repositories And Current Authority

### 1. Standalone platform repo
Location:
- `/Users/anton/Desktop/MagonOS-Standalone`

Role:
- primary platform-of-record
- official local and deploy runtime
- canonical public shell
- canonical standalone backend/operator runtime

Current official startup:
```bash
cd /Users/anton/Desktop/MagonOS-Standalone
./scripts/run_foundation_unified.sh --fresh
```

Primary local surfaces:
- public shell: `http://127.0.0.1:3000/`
- platform dashboard: `http://127.0.0.1:3000/admin-dashboard`
- operator workspace: `http://127.0.0.1:3000/request-workbench`
- operator order workspace: `http://127.0.0.1:3000/orders`
- supplier workspace: `http://127.0.0.1:3000/suppliers`
- direct backend debug: `http://127.0.0.1:8091/`

### 2. Legacy source / donor repo
Location:
- `/Users/anton/Desktop/MagonOS/MagonOS`

Role:
- legacy Odoo shell
- donor/extraction source
- temporary bridge/integration codebase
- Odoo-side inspection and migration support

Important:
- this repo is no longer the primary product runtime
- its `apps/web` copy is legacy donor code only
- its `scripts/start_platform.sh` now delegates to the standalone repo

## Current Product Reality

This is no longer a toy supplier parser.
The standalone repo now contains a real wave1 foundation contour with:
- supplier discovery pipeline
- normalization / enrichment / dedup / scoring
- PostgreSQL-first foundation persistence
- standalone HTTP API
- customer draft -> request -> offer -> order flow
- files/documents contour
- reasons/rules/notifications/timeline/audit
- operator/customer/admin dashboards
- public/product shell in Next.js

The current usable flow is roughly:

`discovery -> canonical company -> scoring/review -> commercial prep -> quote intent -> production handoff -> production board`

## Current Ownership Model

### Standalone-owned now
- raw discovery/extraction state
- evidence/provenance in standalone storage
- canonical supplier/company intelligence
- normalization outputs
- dedup outputs / related standalone review artifacts
- scores
- standalone review/operator-facing workflow state already extracted
- feedback event ledger
- feedback projection/read model
- commercial preparation state already implemented in standalone
- quote intent lifecycle already implemented in standalone
- production handoff/prep state already implemented in standalone
- public shell and operator-facing standalone surfaces

### Odoo/source-owned still
- Odoo ORM/runtime shell
- Odoo XML views / admin shell
- Odoo security model
- `res.partner`
- `crm.lead`
- RFQ / quote / order / accounting contours that are still only Odoo-shaped
- legacy internal workflows not yet reimplemented in standalone
- bridge/export logic that still talks to Odoo

## Current Architecture Statement

### What is true now
- Standalone is the primary platform runtime.
- Odoo is no longer the strategic target platform.
- Odoo is a legacy donor and temporary bridge only.
- The public shell and operator surfaces are now assembled inside the standalone repo.

### What is not true yet
- Odoo is not fully removed.
- The whole commercial/ERP/back-office domain has not been fully replaced.
- The source repo still physically contains duplicate legacy web code and Odoo-bound workflow code.
- Standalone does not yet provide full auth/roles/admin replacement.

## Current Technical Surface Map

### Standalone repo
- backend runtime:
  - `src/magon_standalone/supplier_intelligence/*`
- deploy/runtime entry:
  - `scripts/run_platform.sh`
  - `scripts/run_unified_platform.sh`
  - `scripts/run_deploy.sh`
  - `src/magon_standalone/wsgi.py`
- public shell:
  - `apps/web/*`
- tests:
  - `tests/test_api.py`
  - `tests/test_persistence.py`
  - `tests/test_operations.py`
  - `tests/test_workforce.py`
  - `tests/test_deploy.py`

### Source repo
- Odoo-bound models:
  - `addons/print_broker_core/models/*`
- Odoo-bound services:
  - `addons/print_broker_core/services/*`
- Odoo admin UI:
  - `addons/print_broker_core/views/*`
- Odoo security:
  - `addons/print_broker_core/security/*`
- migration strategy docs:
  - `docs/strategy/*`

## Current Documentation Hierarchy

### Canonical runtime docs
Use the standalone repo first:
- `/Users/anton/Desktop/MagonOS-Standalone/README.md`
- `/Users/anton/Desktop/MagonOS-Standalone/apps/web/README.md`
- `/Users/anton/Desktop/MagonOS-Standalone/docs/deployment.md`
- this file: `/Users/anton/Desktop/MagonOS-Standalone/docs/audit-context.md`

### Legacy strategy/migration docs
Use the source repo for migration thinking and donor inventory:
- `/Users/anton/Desktop/MagonOS/MagonOS/docs/strategy/odoo-full-removal-plan.md`
- `/Users/anton/Desktop/MagonOS/MagonOS/docs/strategy/standalone-platform-target.md`
- `/Users/anton/Desktop/MagonOS/MagonOS/docs/strategy/*`

Important:
- source strategy docs are still useful
- but runtime truth must be verified against the standalone repo code first

## Current Audit Readout

### What is already strong
- standalone runtime exists and runs without Odoo runtime
- SQLite persistence is wired and tested
- product shell exists in standalone
- operator console exists in standalone
- company-centric workflow exists
- feedback contract is narrow, explicit, and not generic entity sync
- core backend tests and standalone web build are passing

### What is structurally weak
- source repo still contains overlapping product code and legacy platform code
- there is still physical duplication of web-layer code between repos
- documentation only recently normalized around one official runtime
- standalone scope is ahead of some docs and behind some strategy docs
- auth/roles/admin replacement is still not implemented as a complete standalone contour
- SQLite is still the practical deployment constraint

### What is risky for audit
- confusing the source repo with the primary runtime
- assuming all Odoo business logic has already been migrated
- overestimating standalone maturity into full ERP replacement
- underestimating how much operator/commercial workflow has already been moved into standalone

## Current Business Readout

### What the product can credibly support now
- discovery and supplier/company intelligence workflow
- manual review and qualification-oriented operator work
- company-centric inspection and decision support
- early commercial preparation around a company
- quote-intent tracking
- production-prep handoff and board visibility
- internal testing/demo of the end-to-end contour on localhost

### What the product does not yet credibly support as final-state business platform
- full sales/CRM replacement
- full order/accounting/ERP ownership
- multi-user governed internal operations with robust auth/permissions
- production-grade horizontal scaling
- fully separated public intake/product workflows backed by mature standalone domain models across all functions

## Recommended Technical Audit Focus

1. Standalone runtime correctness
- verify read/write flows around:
  - companies
  - review queue
  - feedback
  - commercial pipeline
  - quote intents
  - production handoffs
  - production board

2. Boundary discipline
- verify standalone does not reintroduce Odoo runtime dependency
- verify feedback remains narrow and does not become entity sync
- verify public shell and operator shell roles remain clear

3. Persistence durability
- review SQLite schema, migration posture, and constraints
- identify what must change for production-grade persistence later

4. Source repo containment
- verify Odoo-bound logic is truly legacy/bridge only
- identify any still-critical workflows that have not yet been extracted

5. Deployment realism
- review `run_unified_platform.sh`, `run_deploy.sh`, WSGI/gunicorn path, env handling, and operational assumptions

## Recommended Business Audit Focus

1. What customer journey is actually being served now
- lead capture vs operator workflow vs commercial follow-up

2. Which commercial steps are genuinely productized
- and which are still hidden in legacy/Odoo assumptions

3. Which workflows are manual-first by design
- and which ones need stronger system ownership before go-to-market expansion

4. What can be sold/tested now
- supplier discovery / qualification / commercial prep / production-prep contour

5. What should not be sold as “done”
- full ERP replacement
- full CRM replacement
- finance/accounting/process completeness

## Current Concept Decision

The project should now be interpreted as:
- one active standalone platform repo
- one legacy donor/bridge repo
- no further ambiguity about official runtime ownership

That does not mean the migration is complete.
It means the platform-of-record decision is now explicit.

## Immediate Next Audit Questions

### Technical
- Which Odoo-owned models/services are still essential to daily operations?
- Which standalone commercial states are authoritative already vs still transitional?
- What is the minimum auth/admin model required next?
- What persistence path replaces SQLite when single-node limits become blocking?

### Business
- Which user roles must the standalone platform serve next?
- What is the minimum viable external intake / customer-facing flow?
- Which Odoo-shaped workflows should be dropped entirely rather than reimplemented?
- What exact product offer can be demonstrated/sold with the current standalone contour?

## Current Bottom Line

The project is no longer “Odoo with some extra scripts”.
It is also not yet a fully self-sufficient replacement for all business operations.

The correct current framing is:
- standalone platform is the active product-core
- Odoo is legacy/bridge
- the commercial/operator contour is materially underway in standalone
- full business replacement is still incomplete and must be audited domain by domain
