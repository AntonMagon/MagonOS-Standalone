# Repo Workflow

This repository now has an explicit project-memory and git-guard workflow.
The point is to stop losing project context between sessions and to stop calling unpushed local work "done".

## Why this exists

The repo already had instructions in `AGENTS.md` and `.codex/config.toml`, but those files were passive.
They described expectations, but they did not create any enforceable path for:

- restoring project context at the start of work
- updating persistent project memory at the end of work
- blocking commits that skip the memory update
- blocking pushes that skip verification

This document defines the canonical workflow that closes that gap.

## Required files

- `AGENTS.md`
- `docs/current-project-state.md`
- `docs/ru/README.md`
- `docs/ru/current-project-state.md`
- `.codex/config.toml`
- `.codex/project-memory.md`

These are the repo-level context files that must stay aligned.

## Canonical startup

Before substantial work, run:

```bash
./scripts/restore_context.sh
```

What it does:

- confirms the required context files exist
- shows the active repo status
- shows the installed hooks path
- prints the canonical project context files in a predictable order
- includes the required Russian documentation layer

This is the repo-native context restore entrypoint.

## Canonical close-out

After substantial work, update the project memory with:

```bash
./.venv/bin/python scripts/finalize_task.py \
  --summary "short summary" \
  --changed "file or area changed" \
  --verify "./scripts/verify_workflow.sh"
```

What it does:

- runs the verification commands you pass in
- refuses to write a success record if verification fails
- updates `.codex/project-memory.md`
- refreshes the `Active Context` block
- prepends a new worklog entry with timestamp and branch

This is the repo-native task finalization entrypoint.

## Versioned git guards

The repo keeps its hooks in `.githooks/`.
Install them locally with:

```bash
./scripts/install_repo_guards.sh
```

This sets:

```bash
git config core.hooksPath .githooks
```

Installed hooks:

- `pre-commit`
- `pre-push`

### pre-commit

Purpose:

- prevent commits that change product-owned files without also updating `.codex/project-memory.md`
- prevent commits that change product-owned files without also updating the Russian documentation layer in `docs/ru/`
- prevent commits that change code files without added Russian `RU:` explanations in the staged diff
- ensure the memory file still contains the required markers

Product-owned paths for this guard:

- `src/`
- `apps/web/`
- `scripts/`
- `tests/`
- `AGENTS.md`
- `docs/current-project-state.md`
- `docs/ru/`
- `.codex/config.toml`
- `docs/repo-workflow.md`

Russian-document requirement:

- if product-owned files are staged, at least one staged file must be inside `docs/ru/`
- this keeps the Russian explanation layer moving with the code, instead of becoming stale after the first setup

Russian-comment requirement:

- for changed code files, the staged diff must include at least one added line with `RU:` and Cyrillic text
- accepted examples:
  - `# RU: почему здесь нужен этот fallback`
  - `// RU: зачем этот переход делается именно тут`
  - `/* RU: почему это нельзя унести в ERP */`

### pre-push

Purpose:

- prevent pushes that skip repo verification
- prevent pushes that include product-owned changes but no memory update in the outgoing range

Checks:

- `./scripts/verify_workflow.sh`
- `cd apps/web && npm run typecheck` when outgoing commits include `apps/web/`

## Verification contract

Use the smallest command that proves the result, but do not skip recording it.

Canonical repo verification:

```bash
./scripts/verify_workflow.sh
```

This verifies:

- repo workflow scripts and hooks parse cleanly
- backend/unit workflow tests still pass
- optional web typecheck when requested

## GitHub visibility rule

Local commit is not the same as GitHub visibility.

You may only claim the work is visible on GitHub after:

1. the commit exists locally
2. `git push` succeeds

This repo does not auto-push on commit, because that would be unsafe in a dirty working tree.
Instead, it blocks weak commit/push behavior and keeps the required steps explicit.

## Practical use

Minimal disciplined path for a substantial task:

1. `./scripts/restore_context.sh`
2. implement the change
3. update the relevant file in `docs/ru/`
4. add concise Russian comments/docstrings in changed non-obvious logic with explicit `RU:` markers
5. `./scripts/verify_workflow.sh`
6. `./.venv/bin/python scripts/finalize_task.py ...`
7. `git add ...`
8. `git commit -m "..."`
9. `git push`

If step 9 does not happen, the work is still local only.
