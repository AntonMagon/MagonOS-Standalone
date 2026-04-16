---
name: verify-implementation
description: Perform a post-implementation verification pass against intent, tests, docs, and nearby behavior to decide whether the change is actually complete.
---

# verify-implementation

## Purpose
Run a strict post-implementation verification pass after code is already written.

## When to use
- The user asks to re-check whether a task is really done.
- A substantial change touched multiple files or business boundaries.
- You need a final technical verification before commit or push.

## Read first
- `./scripts/restore_context.sh`
- `.codex/project-memory.md`
- changed files
- related tests
- relevant `docs/ru/` explanation files

## Verification questions
- Does the implementation match the intended scope?
- Did it preserve existing behavior?
- Were tests and docs updated where needed?
- Did it introduce architectural drift or scope creep?
- Can the user actually use the result now?

## Execution
1. Reconstruct the exact scope from the changed files and current task.
2. Read the owning code and nearby tests.
3. Run the smallest commands that prove the changed path.
4. Check adjacent behavior that could have regressed.
5. State any remaining risk as evidence, not theory.

## Verification
- task-specific proof command first
- `./scripts/verify_workflow.sh`
- `./scripts/verify_workflow.sh --with-web` when the task touched web code

## Failure note
- This skill is for verification, not for inventing new scope.
- Do not call a task done if one critical path is still unproven.
