---
name: project-visual-map
description: Update and review the visual project map for MagonOS-Standalone so the contour, risks, automations, and current focus stay readable in both docs and the product shell.
---

# project-visual-map

## Purpose
Keep the graphical project map current so the repo state is understandable without rereading the whole codebase.

## When to use
- The user asks for a graphical/structured project map.
- Significant repo state, skills, or automations changed.
- The dashboard copy and visual docs may have drifted from project memory.

## Read first
- `./scripts/restore_context.sh`
- `.codex/project-memory.md`
- `docs/current-project-state.md`
- `docs/ru/current-project-state.md`
- `docs/ru/code-map.md`

## Canonical update path
- `./.venv/bin/python scripts/update_project_visual_map.py`

## Output surfaces
- `docs/ru/visuals/project-map.md`
- `docs/ru/visuals/project-map.json`
- `docs/visuals/project-map.md`
- `docs/visuals/project-map.json`
- `/project-map` in the web shell

## Failure note
- Do not hand-edit generated visual-map docs when the generator can express the change.
- Do not let the visual map drift away from `.codex/project-memory.md`.
