---
name: ci-watch-fix
description: Inspect failing GitHub Actions or repo verification checks, apply the smallest safe fix, and prove the pipeline is green again.
---

# ci-watch-fix

## Purpose
Fix deterministic CI or repo verification failures with minimal diffs.

## When to use
- The user asks to fix CI.
- A push or PR check is red.
- `pre-push` or repo verification catches a real failure that needs code changes.

## Read first
- `./scripts/restore_context.sh`
- `.codex/project-memory.md`
- relevant workflow file under `.github/workflows/` when the failure is GitHub-side

## Execution
1. Identify the exact failing job, command, or local guard.
2. Reproduce the smallest failing command locally.
3. Fix the root cause with the smallest safe patch.
4. Re-run the failing command first.
5. Re-run the broader repo verification only after the narrow failure is green.

## Guardrails
- Minimal diffs only.
- Do not disable tests to make CI green.
- Do not edit workflows unless the failure is actually in the workflow.
- If the failure is flaky, rerun once before patching code.

## Verification
- exact failing command
- `./scripts/verify_workflow.sh`
- `./scripts/verify_workflow.sh --with-web` when web paths are involved

## Failure note
- Do not present a local guess as a CI fix without reproducing it.
- Do not widen a CI fix into unrelated refactors.
