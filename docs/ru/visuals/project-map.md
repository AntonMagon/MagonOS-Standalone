# Визуальная карта проекта

Обновлено: `2026-04-17 04:56 +0700`

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

- Current focus: Added local file-watch autosync with Watchman and Task
- Last verified workflow status: PASS `./scripts/verify_workflow.sh --with-web`
- Biggest operational risk: The repo now auto-runs sync and verification on file changes, but autosync still stops at repo-native actions and does not replace human commit/push decisions or Codex skill dispatch across chats.

## Автоматические контуры контроля

- Hourly Repo Guard
- Hourly Platform Smoke
- Hourly Visual Map
- Weekly Release Gate

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
