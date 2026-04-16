# Визуальная карта проекта

Обновлено: ``2026-04-17 06:50 +07``

## Контур движения

```mermaid
flowchart LR
  Company["Company"] --> Customer["Customer Account"]
  Customer --> Opportunity["Opportunity"]
  Opportunity --> Quote["Quote Intent / RFQ"]
  Quote --> Handoff["Production Handoff"]
  Handoff --> Board["Production Board"]
```

## Что уже принадлежит standalone

- supplier intelligence pipeline
- normalization / enrichment / dedup / scoring
- review queue
- routing / qualification decisions
- feedback ledger / projection
- workforce estimation

## Что сейчас является ядром контура

- company
- commercial/customer context
- opportunity
- quote intent / RFQ boundary
- production handoff
- production board

## Где остаётся риск overlap

- customer/account identity
- opportunity/lead ownership
- RFQ / quote boundary

## Что не должно расползаться в scope

- accounting
- invoice / payment
- full ERP order management
- giant generic CRM
- broad Odoo entity mirroring
- source repo feature growth

## Активный контекст

- Current focus: Keep runtime automation green while architecture work continues
- Last verified workflow status: PASS `./.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`, PASS `cd apps/web && npm run build`, PASS `./scripts/platform_smoke_check.sh`, PASS `./scripts/run_perf_suite.sh smoke`, PASS `./.venv/bin/python scripts/run_periodic_checks.py --mode manual`, PASS `./scripts/verify_workflow.sh --with-web`
- Biggest operational risk: Cold-start dev-shell latency can still be worse than steady-state performance; perf smoke is now robust but still measures a development runtime, not a production shell.

## Автоматические контуры контроля

- Hourly Repo Guard
- Hourly Platform Smoke
- Hourly Visual Map
- Weekly Release Gate
- Launchd Periodic Checks

## Активные project skills

- audit-docs-vs-runtime
- ci-watch-fix
- docs-sync-curator
- donor-boundary-audit
- git-safe-commit
- operate-platform
- operate-standalone-intelligence
- project-visual-map
- release-readiness-gate
- skill-pattern-scan
- verify-implementation
- web-regression-pass
