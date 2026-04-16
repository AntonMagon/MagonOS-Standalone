---
name: audit-docs-vs-runtime
description: Audit the standalone repo for mismatches between code, tests, runtime, AGENTS rules, and supporting docs, then report only concrete drift.
---

# audit-docs-vs-runtime

## Purpose
Audit the standalone repo for mismatches between code, tests, runtime, AGENTS rules, and supporting docs.

## When to use
- The user asks what is true in the project right now.
- The user asks whether docs match runtime behavior.
- The user asks whether current operating rules still match the standalone platform.
- The user asks what is implemented versus what is only described.

## Truth order
- Trust `src/`, `apps/web/`, `scripts/`, and `tests/` first.
- Then trust `AGENTS.md` and `.codex/config.toml`.
- Then trust `.codex/project-memory.md` and `docs/ru/`.
- Then compare `docs/`.
- Use the source repo only as donor context, never as default runtime truth.

## Read first
- `./scripts/restore_context.sh`
- `AGENTS.md`
- `.codex/config.toml`
- `.codex/project-memory.md`
- `docs/ru/README.md`
- `docs/ru/current-project-state.md`
- `docs/audit-context.md`
- `docs/business-logic-parity-audit.md`
- `docs/operating-layer-migration-audit.md`

## Read when relevant
- `docs/deployment.md`
- `apps/web/README.md`
- donor files in `/Users/anton/Desktop/MagonOS/MagonOS/*`

## Execution
1. Check repo state with `git status --short --branch`.
2. Inspect the exact standalone entrypoints relevant to the audit.
3. Inspect the owning runtime code and tests.
4. Compare docs claims against actual standalone behavior.
5. If donor docs conflict with standalone code, mark them as donor-only or stale.
6. Run the smallest command that proves the runtime claim.
7. If the audit changes repo-owned truth, update `.codex/project-memory.md` and at least one relevant file in `docs/ru/`.
8. Report only concrete matches, drift, and required fixes.

## Verification
- `./scripts/restore_context.sh --check`
- `./scripts/verify_workflow.sh`
- `./scripts/verify_workflow.sh --with-web` when the audit touched `apps/web/`

## Exit criteria
- The audit states what is true now.
- Every mismatch points to exact files.
- Donor assumptions are separated from active standalone reality.
- The Russian documentation layer is not left stale after the audit.
