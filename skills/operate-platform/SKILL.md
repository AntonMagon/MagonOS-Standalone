# operate-platform

## Purpose
Start and verify the active standalone MagonOS platform through its canonical standalone entrypoints.

## When to use
- The user wants the actual local platform running.
- The user wants public shell plus operator surfaces together.
- The user wants the active standalone product, not the old Odoo shell.

## Read first
- `./scripts/restore_context.sh`
- `.codex/project-memory.md`
- `docs/ru/current-project-state.md`

## Execution
- Unified platform:
  - `./scripts/run_unified_platform.sh --fresh`
- Backend only:
  - `./scripts/run_platform.sh --fresh --port 8091`

## Runtime ownership
- `scripts/run_unified_platform.sh` is the canonical full local startup path.
- `scripts/run_platform.sh` is the canonical backend-only startup path.
- Public shell lives in `apps/web`.
- Product-core runtime lives in `src/magon_standalone`.

## Verification
- `./scripts/restore_context.sh --check`
- `curl http://127.0.0.1:8091/health`
- open `http://127.0.0.1:3000/`
- open `http://127.0.0.1:3000/ui/companies`
- `./scripts/verify_workflow.sh --with-web` when changes were made while operating the platform

## Failure note
- Do not route the user back to the source repo startup path.
- Do not invent manual Odoo startup as a fallback for the active product.
