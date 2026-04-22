# Project Visual Map

Updated: ``2026-04-23 01:32 +07``

## Flow contour

```mermaid
flowchart LR
  Company["Company"] --> Customer["Customer Account"]
  Customer --> Opportunity["Opportunity"]
  Opportunity --> Quote["Quote Intent / RFQ"]
  Quote --> Handoff["Production Handoff"]
  Handoff --> Board["Production Board"]
```

## Standalone-owned capabilities

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

## Validated contour

- company
- request draft / intake boundary
- commercial/customer context
- opportunity
- quote intent / RFQ boundary
- production handoff
- production board

## Dangerous overlap

- customer/account identity
- opportunity/lead ownership
- RFQ / quote boundary

## Out of scope

- accounting
- invoice / payment
- full ERP order management
- giant generic CRM
- broad legacy entity mirroring
- source repo feature growth
