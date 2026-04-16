# operate-standalone-intelligence

## Purpose
Run and verify the standalone supplier-intelligence and operator contour without guessing the owning script or runtime path.

## When to use
- The user asks to run or verify the standalone pipeline.
- The user asks to inspect persisted standalone results.
- The user asks to verify the current company -> opportunity -> quote intent -> handoff contour.

## Read first
- `./scripts/restore_context.sh`
- `.codex/project-memory.md`
- `docs/ru/current-project-state.md`
- `docs/ru/code-map.md`

## Canonical commands
- Fixture-backed pipeline seed:
  - `./.venv/bin/python scripts/run_pipeline.py --fixture tests/fixtures/vn_suppliers_raw.json`
- Backend API:
  - `./scripts/run_platform.sh --fresh --port 8091`
- Result inspection:
  - `./.venv/bin/python scripts/inspect_results.py --table companies`
  - `./.venv/bin/python scripts/inspect_results.py --table review-queue`
  - `./.venv/bin/python scripts/inspect_results.py --table feedback-status`

## Verified contour to keep in mind
- company
- commercial/customer context
- opportunity
- quote intent / RFQ boundary
- production handoff
- production board

## Output contract
State exactly which path was verified:
- pipeline
- backend API
- operator pages
- persistence rows

## Failure note
- Do not describe donor Odoo flows as active runtime behavior.
- Do not claim full ERP/CRM parity if only the extracted contour was verified.
- If the verified contour changed, update `.codex/project-memory.md` and at least one relevant file in `docs/ru/`.
