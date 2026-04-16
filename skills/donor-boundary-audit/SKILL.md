---
name: donor-boundary-audit
description: Inspect the legacy donor repo only for business-rule extraction or boundary checks, then classify what stays donor-only versus what belongs in standalone.
---

# donor-boundary-audit

## Purpose
Audit the donor repo without letting donor runtime logic silently become active standalone truth.

## When to use
- A task explicitly requires Odoo/donor inspection.
- You need to extract business rules, validations, or transitions from the legacy repo.
- You need to verify whether a behavior is donor-only, bridge-only, or worth reconstruction in standalone.

## Read first
- `./scripts/restore_context.sh`
- `AGENTS.md`
- `docs/current-project-state.md`
- `docs/ru/current-project-state.md`
- donor files under `/Users/anton/Desktop/MagonOS/MagonOS`

## Classification contract
Every donor behavior inspected must be classified as:
- `keep`
- `adapt`
- `drop`
- `reconstruct from evidence`

## Execution
1. Read only the relevant donor files.
2. Extract business rules, validations, state transitions, and ownership semantics.
3. Map them against current standalone ownership.
4. State clearly whether the result changes standalone code, docs only, or nothing.

## Failure note
- Do not treat donor code as active runtime truth.
- Do not copy Odoo shapes mechanically.
- Do not modify the donor repo unless the task explicitly requires it.
