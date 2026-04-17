---
name: operate-platform
description: Start and verify the active standalone MagonOS platform through its canonical runtime entrypoints and local surfaces.
---

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
- Unified foundation platform:
  - `./scripts/run_foundation_unified.sh --fresh`
- Foundation backend only:
  - `./.venv/bin/python scripts/run_foundation_api.py --host 127.0.0.1 --port 8091`
- Compatibility-only legacy startup:
  - `MAGON_FOUNDATION_LEGACY_ENABLED=true ./scripts/run_foundation_unified.sh --fresh`
  - `./scripts/run_unified_platform.sh --fresh`
  - `./scripts/run_platform.sh --fresh --port 8091`

## Runtime ownership
- `scripts/run_foundation_unified.sh` is the canonical full local startup path for wave1.
- `scripts/run_foundation_api.py` is the canonical backend-only startup path for wave1.
- Public shell lives in `apps/web`.
- Product-core runtime lives in `src/magon_standalone`.
- Legacy shell entrypoints are compatibility-only and must not be treated as the normal runtime.

## Resource guard
- On macOS Docker/Colima hosts, prefer a small default VM first:
  - `colima start --cpu 2 --memory 2 --disk 20 --vm-type vz`
- Expand Colima resources only when the current task proves it needs more.
- Do not silently start Colima with a 6 GB memory cap for routine local checks.
- Verified steady-state compose usage is currently about `430-450 MiB` across `api + worker + web + db + redis + caddy`, so `2 GB` is enough for routine local runtime and rebuilds.
- Move to `3 GB` only when doing concurrent rebuilds plus browser-heavy work on the same host.
- Move to `4 GB` only for clearly heavier tasks such as Playwright/browser automation, extra services, or substantially larger frontend builds.
- Web runtime baseline is Node 22 when building or running `apps/web`.

## Verification
- `./scripts/restore_context.sh --check`
- `curl http://127.0.0.1:8091/health/ready`
- open `http://127.0.0.1:3000/`
- open `http://127.0.0.1:3000/login`
- `./scripts/verify_workflow.sh --with-web` when changes were made while operating the platform

## Failure note
- Do not route the user back to the source repo startup path.
- Do not invent manual Odoo startup as a fallback for the active product.
