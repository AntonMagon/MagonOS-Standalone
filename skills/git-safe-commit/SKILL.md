# git-safe-commit

## Purpose
Close a finished standalone task with narrow staging, verification, and one intentional commit when the user explicitly asks for git actions.

## When to use
- The user explicitly asks to commit, stage, push, or prepare a PR.
- The task is complete and verification already passed.

## Execution
1. Run `./scripts/restore_context.sh` if the task was substantial.
2. Run `git status --short --branch`.
3. Keep the commit scope narrow.
4. Re-run the task-specific verification command.
5. Ensure `.codex/project-memory.md` is updated for substantial repo changes.
6. Ensure at least one relevant file in `docs/ru/` is updated for product-owned changes.
7. Stage only intended files.
8. Review `git diff --cached --stat`.
9. Commit with a short, clear message.
10. Push only if the user explicitly requested it.

## Failure note
- Do not auto-commit because a task is done.
- Do not stage unrelated dirty files.
- Do not pretend push/PR happened unless it actually happened.
- Do not bypass the repo guard contract around `.codex/project-memory.md` and `docs/ru/`.
