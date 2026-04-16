# AGENTS.md

## Mission
You are working on the active MagonOS standalone platform.
The goal is working, testable, practical product progress.
Do not waste runs on wrapper churn, README cosmetics, or architecture theater.

## Repository Authority
- Active product repo: `/Users/anton/Desktop/MagonOS-Standalone`
- Legacy donor / bridge repo: `/Users/anton/Desktop/MagonOS/MagonOS`
- Standalone is the primary platform-of-record.
- Source repo is donor/inspection only unless a task explicitly requires boundary work there.

## Default Work Area
- Default code changes happen only in this repository.
- Read the source repo only for:
  - donor inspection
  - extraction planning
  - explicit bridge/integration boundary work
- Do not drift into source repo normalization, wrapper cleanup, or parallel feature work.

## Current Architecture Truth
For canonical current-state truth, read `docs/current-project-state.md`.

## Out Of Scope By Default
Do not silently broaden into:
- accounting
- invoice / payment
- full ERP order management
- giant generic CRM
- broad entity mirroring from Odoo
- Odoo runtime reintroduction
- source repo feature growth

## Work Discipline
- Inspect the minimum set of files needed.
- Prefer runnable local results.
- Trust code, tests, and runtime over stale docs.
- If docs conflict with code, trust code first.
- Do not hallucinate missing business logic.
- Do not claim parity that does not exist.
- Do not present scaffolding as done.
- Keep changes small, complete, and verifiable.

## Priority Discipline
- Product-core correctness beats documentation cleanup.
- Business-module progress beats wrapper normalization.
- Verification beats narrative.
- Narrow, explicit ownership beats vague overlap.

## Donor Inspection Rules
When donor inspection is required:
1. Read only the relevant source files.
2. Extract business rules, validations, transitions, and ownership semantics.
3. Classify donor behavior as:
   - keep
   - adapt
   - drop
   - reconstruct from evidence
4. Do not copy Odoo shapes mechanically.
5. Do not modify the source repo unless the task explicitly says so.

## Verification Discipline
Use the smallest command that proves the result.
Canonical commands and local surfaces are defined in `docs/current-project-state.md`.

## Repo Memory And Execution Guards
- Restore substantial task context with `./scripts/restore_context.sh`.
- Persistent project memory lives in `.codex/project-memory.md`.
- Substantial work is not done until `.codex/project-memory.md` is updated with a verification-backed entry.
- Finalize substantial work with `./.venv/bin/python scripts/finalize_task.py ...`.
- Versioned repo hooks live in `.githooks/` and are installed with `./scripts/install_repo_guards.sh`.
- Do not claim GitHub visibility until a real `git push` succeeds.

## Russian Documentation And Comment Contract
- Russian repo documentation lives in `docs/ru/`.
- Product-owned changes must update at least one relevant file in `docs/ru/` in the same commit.
- Non-obvious business logic, routing logic, locale logic, persistence transitions, and workflow guards must have concise Russian comments or docstrings near the changed code.
- For changed code files, at least one added Russian explanatory line with an explicit `RU:` marker must be present in the staged diff.
- Do not add noise comments. Add Russian comments only where they explain purpose, boundary, or non-obvious behavior.
- If the code changed and no Russian explanation was needed, that decision must still be justified by the code being trivial.

## Reporting Contract
For substantial tasks, report:
1. repo worked in
2. what was found
3. what changed
4. what was verified
5. exact commands actually run
6. exact local URLs to open when relevant
7. what was intentionally not done
8. biggest remaining gap or risk

## Failure Patterns
Treat these as drift/failure:
- spending the run mainly on README/docs/startup wrappers
- improving the source repo when the task belongs in standalone
- calling Odoo refs “ownership” instead of traceability
- widening feedback into generic sync
- building ERP/accounting scope without an explicit task
- hiding business gaps behind UI work

## Done
A task is done only when:
- the result is implemented or the exact blocker is stated
- the relevant path is verified with a real command
- ownership boundaries remain explicit
- no accidental Odoo runtime dependency was introduced
