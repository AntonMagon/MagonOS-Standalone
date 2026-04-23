---
name: web-regression-pass
description: Run persistent browser regression checks for the standalone web shell and operator surfaces, then fix or report concrete breakage with verified evidence.
---

# web-regression-pass

## Purpose
Run a practical browser regression pass for the standalone web shell and operator surfaces.

## When to use
- The user asks whether the frontend still works.
- A task changed `apps/web/` or operator-facing routes.
- You need a repeatable smoke/regression path instead of manual clicking.

## Read first
- `./scripts/restore_context.sh`
- `docs/ru/current-project-state.md`
- `docs/ru/code-map.md`
- `apps/web/README.md` when the web app changed significantly

## Target surfaces
- `http://127.0.0.1:3000/`
- `http://127.0.0.1:3000/dashboard`
- `http://127.0.0.1:3000/request-workbench`
- `http://127.0.0.1:3000/orders`
- `http://127.0.0.1:3000/suppliers`
- `http://127.0.0.1:3000/admin-config`

## Execution
1. Start the smallest runtime needed for the target surfaces.
2. Prefer persistent Playwright tests over ad-hoc browser driving.
3. Cover the main business path first:
   - public shell loads
   - dashboard loads
   - request workbench loads
   - order workbench loads
   - supplier/admin surfaces load
4. If a path fails, identify the root cause and fix the smallest owning file set.
5. Re-run the same regression path after the fix.

## Verification
- `./scripts/verify_workflow.sh --with-web`
- `cd apps/web && npm run typecheck`
- relevant Playwright run once tests exist for the touched path

## Failure note
- Do not call a screenshot pass "verified".
- Do not stop at "page loads" if the changed path includes interaction logic.
- If the regression pass changed repo-owned truth, update `.codex/project-memory.md` and relevant `docs/ru/`.
