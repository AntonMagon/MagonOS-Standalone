# git-safe-commit

## Purpose
Close a finished standalone task with narrow staging, verification, and one intentional commit when the user explicitly asks for git actions.

## When to use
- The user explicitly asks to commit, stage, push, or prepare a PR.
- The task is complete and verification already passed.

## Execution
1. Run `git status --short --branch`.
2. Keep the commit scope narrow.
3. Re-run the task-specific verification command.
4. Stage only intended files.
5. Review `git diff --cached --stat`.
6. Commit with a short, clear message.
7. Push only if the user explicitly requested it.

## Failure note
- Do not auto-commit because a task is done.
- Do not stage unrelated dirty files.
- Do not pretend push/PR happened unless it actually happened.
