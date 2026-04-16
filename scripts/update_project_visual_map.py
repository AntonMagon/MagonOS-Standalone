#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_STATE_PATH = REPO_ROOT / "docs/current-project-state.md"
CURRENT_STATE_RU_PATH = REPO_ROOT / "docs/ru/current-project-state.md"
PROJECT_MEMORY_PATH = REPO_ROOT / ".codex/project-memory.md"
RU_OUTPUT_DIR = REPO_ROOT / "docs/ru/visuals"
EN_OUTPUT_DIR = REPO_ROOT / "docs/visuals"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section_bullets(text: str, heading: str) -> list[str]:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match:
        return []
    lines = []
    in_bullet_block = False
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if line.startswith("- "):
            in_bullet_block = True
            lines.append(line[2:].strip())
            continue
        if in_bullet_block and line:
            break
    return lines


def _label_bullets(text: str, label: str) -> list[str]:
    bullets = []
    armed = False
    for raw in text.splitlines():
        line = raw.strip()
        if line == f"{label}:":
            armed = True
            continue
        if not armed:
            continue
        if line.startswith("- "):
            bullets.append(line[2:].strip())
            continue
        if bullets:
            break
    return bullets


def _section_or_label_bullets(text: str, heading: str, label: str) -> list[str]:
    bullets = _section_bullets(text, heading)
    if bullets:
        return bullets
    # RU: В английском current-state этот блок хранится как label-список, и без fallback визуальная карта теряла owned capabilities.
    return _label_bullets(text, label)


def _active_context(memory_text: str) -> dict[str, str]:
    match = re.search(
        r"<!-- ACTIVE:START -->(.*?)<!-- ACTIVE:END -->",
        memory_text,
        re.S,
    )
    if not match:
        return {}
    payload: dict[str, str] = {}
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        key, _, value = line[2:].partition(":")
        payload[key.strip().lower().replace(" ", "_")] = value.strip()
    return payload


def _recent_worklog(memory_text: str, limit: int = 3) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for heading, body in re.findall(r"^### (.+?)\n(.*?)(?=^### |\Z)", memory_text, re.M | re.S):
        entry = {"heading": heading.strip()}
        summary_match = re.search(r"- Summary: (.+)", body)
        risk_match = re.search(r"- Risk:\n(?:  - .+\n?)+|- Risk: (.+)", body)
        if summary_match:
            entry["summary"] = summary_match.group(1).strip()
        if risk_match:
            entry["risk"] = risk_match.group(1).strip() if risk_match.group(1) else "See worklog entry"
        entries.append(entry)
        if len(entries) >= limit:
            break
    return entries


def _skill_names() -> list[str]:
    names: list[str] = []
    for skill_file in sorted((REPO_ROOT / "skills").glob("*/SKILL.md")):
        text = _read(skill_file)
        frontmatter = re.search(r"^---\n(.*?)\n---", text, re.S)
        if frontmatter:
            name_match = re.search(r"^name:\s*(.+)$", frontmatter.group(1), re.M)
            if name_match:
                names.append(name_match.group(1).strip())
                continue
        heading_match = re.search(r"^#\s+(.+)$", text, re.M)
        names.append((heading_match.group(1) if heading_match else skill_file.parent.name).strip())
    return names


def _build_payload() -> dict[str, object]:
    state_en = _read(CURRENT_STATE_PATH)
    state_ru = _read(CURRENT_STATE_RU_PATH)
    memory_text = _read(PROJECT_MEMORY_PATH)
    active = _active_context(memory_text)

    # RU: Автоматы держим прямо в payload, чтобы docs и /project-map рендерили один и тот же контрольный контур без ручной синхронизации.
    return {
        "generated_at": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z"),
        "repo": {
            "active_repo": "/Users/anton/Desktop/MagonOS-Standalone",
            "donor_repo": "/Users/anton/Desktop/MagonOS/MagonOS",
        },
        "validated_contour_en": _section_bullets(state_en, "Validated standalone contour"),
        "validated_contour_ru": _section_bullets(state_ru, "Что уже подтверждено в standalone-контуре"),
        "owned_capabilities_en": _section_or_label_bullets(
            state_en,
            "Also already standalone-owned",
            "Also already standalone-owned",
        ),
        "owned_capabilities_ru": _section_bullets(state_ru, "Что уже принадлежит standalone"),
        "danger_overlap_en": _section_bullets(state_en, "Current dangerous overlap"),
        "danger_overlap_ru": _section_bullets(state_ru, "Где сейчас опасный overlap"),
        "out_of_scope_en": _section_bullets(state_en, "Still out of scope by default"),
        "out_of_scope_ru": _section_bullets(state_ru, "Что по умолчанию вне scope"),
        "active_context": active,
        "recent_worklog": _recent_worklog(memory_text),
        "skills": _skill_names(),
        "automations": [
            "Hourly Repo Guard",
            "Hourly Platform Smoke",
            "Hourly Visual Map",
            "Weekly Release Gate",
        ],
    }


def _write_ru_markdown(payload: dict[str, object]) -> None:
    RU_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md = f"""# Визуальная карта проекта

Обновлено: `{payload["generated_at"]}`

## Контур движения

```mermaid
flowchart LR
  Company["Company"] --> Customer["Customer Account"]
  Customer --> Opportunity["Opportunity"]
  Opportunity --> Quote["Quote Intent / RFQ"]
  Quote --> Handoff["Production Handoff"]
  Handoff --> Board["Production Board"]
```

## Что уже принадлежит standalone

{chr(10).join(f"- {item}" for item in payload["owned_capabilities_ru"])}

## Что сейчас является ядром контура

{chr(10).join(f"- {item}" for item in payload["validated_contour_ru"])}

## Где остаётся риск overlap

{chr(10).join(f"- {item}" for item in payload["danger_overlap_ru"])}

## Что не должно расползаться в scope

{chr(10).join(f"- {item}" for item in payload["out_of_scope_ru"])}

## Активный контекст

- Current focus: {payload["active_context"].get("current_focus", "—")}
- Last verified workflow status: {payload["active_context"].get("last_verified_workflow_status", "—")}
- Biggest operational risk: {payload["active_context"].get("biggest_operational_risk", "—")}

## Автоматические контуры контроля

{chr(10).join(f"- {item}" for item in payload["automations"])}

## Активные project skills

{chr(10).join(f"- {item}" for item in payload["skills"])}
"""
    (RU_OUTPUT_DIR / "project-map.md").write_text(md, encoding="utf-8")
    (RU_OUTPUT_DIR / "project-map.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_en_markdown(payload: dict[str, object]) -> None:
    EN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    md = f"""# Project Visual Map

Updated: `{payload["generated_at"]}`

## Flow contour

```mermaid
flowchart LR
  Company["Company"] --> Customer["Customer Account"]
  Customer --> Opportunity["Opportunity"]
  Opportunity --> Quote["Quote Intent / RFQ"]
  Quote --> Handoff["Production Handoff"]
  Handoff --> Board["Production Board"]
```

## Standalone-owned capabilities

{chr(10).join(f"- {item}" for item in payload["owned_capabilities_en"])}

## Validated contour

{chr(10).join(f"- {item}" for item in payload["validated_contour_en"])}

## Dangerous overlap

{chr(10).join(f"- {item}" for item in payload["danger_overlap_en"])}

## Out of scope

{chr(10).join(f"- {item}" for item in payload["out_of_scope_en"])}
"""
    (EN_OUTPUT_DIR / "project-map.md").write_text(md, encoding="utf-8")
    (EN_OUTPUT_DIR / "project-map.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    payload = _build_payload()
    _write_ru_markdown(payload)
    _write_en_markdown(payload)
    print(f"Updated {RU_OUTPUT_DIR / 'project-map.md'}")
    print(f"Updated {EN_OUTPUT_DIR / 'project-map.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
