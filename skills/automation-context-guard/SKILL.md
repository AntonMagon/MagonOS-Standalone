---
name: automation-context-guard
description: Force every recurring automation to restore the same standalone repo context, trust the same source-of-truth files, and use only canonical runtime and verification commands.
---

# automation-context-guard

## Purpose
Make recurring automations deterministic.

This skill exists so repo checks, audits, digests, and reviews do not invent their own context.
Every automation that touches this repository should start from the same standalone truth and the same canonical commands.

## Use this skill when
- A Codex automation runs against `/Users/anton/Desktop/MagonOS-Standalone`.
- A scheduled audit, review, digest, or release gate needs repo context first.
- The task could drift if it reads only part of the docs or skips restore-context.

## Mandatory context restore
Always start with:
- `./scripts/restore_context.sh --check`

Then treat these files as the minimum repo context bundle:
- `AGENTS.md`
- `README.md`
- `.codex/config.toml`
- `.codex/project-memory.md`
- `docs/current-project-state.md`
- `docs/ru/current-project-state.md`
- `docs/repo-workflow.md`
- `docs/ru/repo-workflow.md`
- `docs/ru/code-map.md`

## Context truth rules
- Trust runtime, tests, and canonical scripts over stale narrative.
- Treat `.codex/project-memory.md` as current execution memory, not as product truth by itself.
- Treat `docs/current-project-state.md` and `docs/ru/current-project-state.md` as architecture/scope truth.
- Treat `AGENTS.md` and `docs/repo-workflow.md` as workflow and guard truth.
- Do not widen scope beyond validated standalone contour unless the repo explicitly says so.

## Canonical commands
Choose the smallest command that proves the automation's claim.

- Repo guard / docs drift:
  - `./.venv/bin/python scripts/sync_operating_docs.py`
  - `./scripts/verify_workflow.sh`
- Web-aware verification:
  - `./scripts/verify_workflow.sh --with-web`
- Locale guard:
  - `./.venv/bin/python scripts/check_russian_locale_integrity.py --static-only`
- Visual map:
  - `./.venv/bin/python scripts/update_project_visual_map.py`
- Platform smoke:
  - `./scripts/platform_smoke_check.sh`
- Full local platform:
  - `./scripts/run_unified_platform.sh --fresh`
- Backend only:
  - `./scripts/run_platform.sh --fresh --port 8091`

## Automation writing rules
- Report only concrete findings, drift, or verified green status.
- Prefer exact file paths, commands, and URLs.
- Do not rewrite docs or code unless the automation explicitly exists to update them.
- Do not claim a result is valid if `restore_context` or the relevant canonical command was skipped.

## Failure note
- If restore-context fails, the automation is not in project context yet. Report that first.
- If a task needs donor/Odoo context, use donor-only inspection rules and keep standalone ownership explicit.
