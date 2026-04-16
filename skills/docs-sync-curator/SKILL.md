---
name: docs-sync-curator
description: Audit and synchronize repo docs, Russian docs, AGENTS rules, config references, and script references against the actual standalone codebase.
---

# docs-sync-curator

## Purpose
Keep the repo documentation layer aligned with actual standalone runtime truth.

## When to use
- The user asks whether docs still match the code.
- A change touched commands, repo workflow, runtime surfaces, or project rules.
- Russian and English docs may have drifted apart.

## Read first
- `./scripts/restore_context.sh`
- `AGENTS.md`
- `.codex/config.toml`
- `.codex/project-memory.md`
- `docs/`
- `docs/ru/`

## Execution
1. Inspect the exact owning code and scripts first.
2. Compare repo docs against runtime truth in this order:
   - `src/`
   - `apps/web/`
   - `scripts/`
   - `tests/`
   - `AGENTS.md`
   - `docs/`
3. Fix stale references, missing commands, mismatched paths, and contradictory claims.
4. Keep `docs/ru/` aligned with the same truth, not as a separate narrative.

## Verification
- `./scripts/restore_context.sh --check`
- `./scripts/verify_workflow.sh`
- grep or direct file checks for corrected paths/commands when relevant

## Failure note
- Do not update docs from memory when the code is easy to inspect.
- Do not let `docs/ru/` become a translation layer for stale English docs.
