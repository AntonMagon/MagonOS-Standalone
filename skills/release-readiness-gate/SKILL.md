---
name: release-readiness-gate
description: Make a hard readiness verdict for merge, handoff, demo, or release based on runtime, verification, docs, and operational evidence.
---

# release-readiness-gate

## Purpose
Decide whether the current state is ready for merge, handoff, demo, staging, or production-like use.

## When to use
- The user asks whether the project is ready to ship or hand off.
- A milestone needs a hard verdict instead of another implementation pass.
- You need a go / caveat / stop decision.

## Verdict contract
Return exactly one:
- `Ready`
- `Ready with caveats`
- `Not ready`

## Read first
- `./scripts/restore_context.sh`
- `.codex/project-memory.md`
- `docs/current-project-state.md`
- `docs/ru/current-project-state.md`
- changed runtime and deployment entrypoints

## Readiness dimensions
- build and runtime
- verification gates
- configuration and environment assumptions
- docs and handoff quality
- operational visibility and failure handling
- known caveats versus blockers

## Execution
1. Define the actual release target.
2. Verify the owning runtime path.
3. Verify quality gates that matter for that target.
4. Separate blockers from caveats.
5. Tie the final verdict to evidence.

## Verification
- `./scripts/verify_workflow.sh`
- target-specific runtime command from `docs/current-project-state.md`

## Failure note
- Do not confuse "tests pass" with "release ready".
- Do not avoid the final verdict.
