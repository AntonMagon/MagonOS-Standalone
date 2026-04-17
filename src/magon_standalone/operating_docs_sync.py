"""Auto-sync helpers for root operating docs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

AGENTS_SYNC_START = "<!-- AUTO-SYNC:AGENTS:START -->"
AGENTS_SYNC_END = "<!-- AUTO-SYNC:AGENTS:END -->"
README_SYNC_START = "<!-- AUTO-SYNC:README:START -->"
README_SYNC_END = "<!-- AUTO-SYNC:README:END -->"
ACTIVE_START = "<!-- ACTIVE:START -->"
ACTIVE_END = "<!-- ACTIVE:END -->"


@dataclass(frozen=True)
class OperatingDocsPayload:
    updated_at: str
    focus: str
    verified_status: str
    risk: str
    validated_contour: list[str]
    owned_capabilities: list[str]
    runtime_surfaces: list[str]
    repo_skills: list[str]
    active_automations: list[str]


def _strip_wrapping_backticks(value: str) -> str:
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1]
    return value


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _replace_block(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"missing_marker_block:{start_marker}")
    end += len(end_marker)
    return text[:start] + replacement + text[end:]


def _section_bullets(text: str, heading: str) -> list[str]:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match:
        return []
    bullets: list[str] = []
    in_block = False
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if line.startswith("- "):
            in_block = True
            bullets.append(line[2:].strip())
            continue
        if in_block and line:
            break
    return bullets


def _label_bullets(text: str, label: str) -> list[str]:
    bullets: list[str] = []
    armed = False
    active_label_variants = {f"{label}:", f"- {label}:"}
    for raw in text.splitlines():
        line = raw.strip()
        if line in active_label_variants:
            armed = True
            continue
        if not armed:
            continue
        if line.startswith("- ") and line.endswith(":") and line not in active_label_variants:
            break
        if line.startswith("- "):
            bullets.append(line[2:].strip())
            continue
        if bullets:
            break
    return bullets


def _active_context(memory_text: str) -> dict[str, str]:
    match = re.search(rf"{re.escape(ACTIVE_START)}(.*?){re.escape(ACTIVE_END)}", memory_text, re.S)
    if not match:
        raise ValueError("missing_active_markers")
    payload: dict[str, str] = {}
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        key, _, value = line[2:].partition(":")
        payload[key.strip().lower().replace(" ", "_")] = value.strip()
    return payload


def _repo_skill_names(repo_root: Path) -> list[str]:
    names: list[str] = []
    for skill_file in sorted((repo_root / "skills").glob("*/SKILL.md")):
        text = _read(skill_file)
        frontmatter = re.search(r"^---\n(.*?)\n---", text, re.S)
        if frontmatter:
            match = re.search(r"^name:\s*(.+)$", frontmatter.group(1), re.M)
            if match:
                names.append(match.group(1).strip())
                continue
        names.append(skill_file.parent.name)
    return names


def _active_automation_names(codex_home: Path) -> list[str]:
    names: list[str] = []
    automation_root = codex_home / "automations"
    if not automation_root.is_dir():
        return names
    for toml_path in sorted(automation_root.glob("*/automation.toml")):
        text = _read(toml_path)
        if 'status = "ACTIVE"' not in text:
            continue
        match = re.search(r'^name = "(.+)"$', text, re.M)
        if match:
            names.append(match.group(1).strip())
    return names


def _fallback_active_automations(repo_root: Path) -> list[str]:
    for path in (repo_root / "AGENTS.md", repo_root / "README.md"):
        if not path.is_file():
            continue
        bullets = _label_bullets(_read(path), "Active repo automations")
        if bullets:
            return bullets
    return []


def build_payload(repo_root: Path) -> OperatingDocsPayload:
    current_state = _read(repo_root / "docs/current-project-state.md")
    memory_text = _read(repo_root / ".codex/project-memory.md")
    active = _active_context(memory_text)
    codex_home = Path.home() / ".codex"
    active_automations = _active_automation_names(codex_home) or _fallback_active_automations(repo_root)
    # RU: Корневые docs собираются из канонической repo truth, а не из ручных правок в AGENTS/README.
    # RU: В CI у runner обычно нет локального ~/.codex/automations, поэтому для стабильного check-mode держим repo-backed fallback.
    return OperatingDocsPayload(
        updated_at=_strip_wrapping_backticks(active.get("updated_at", "unknown")),
        focus=active.get("current_focus", "unknown"),
        verified_status=active.get("last_verified_workflow_status", "unknown"),
        risk=active.get("biggest_operational_risk", "unknown"),
        validated_contour=_section_bullets(current_state, "Validated standalone contour"),
        owned_capabilities=_label_bullets(current_state, "Also already standalone-owned"),
        runtime_surfaces=_section_bullets(current_state, "Runtime surfaces"),
        repo_skills=_repo_skill_names(repo_root),
        active_automations=active_automations,
    )


def render_agents_block(payload: OperatingDocsPayload) -> str:
    lines = [
        AGENTS_SYNC_START,
        f"- Auto-synced at: `{payload.updated_at}`",
        f"- Current focus: {payload.focus}",
        f"- Last verified workflow status: {payload.verified_status}",
        f"- Biggest operational risk: {payload.risk}",
        "- Validated contour:",
    ]
    lines.extend([f"  - {item}" for item in payload.validated_contour])
    lines.append("- Active repo automations:")
    lines.extend([f"  - {item}" for item in payload.active_automations] or ["  - none detected"])
    lines.append("- Repo-local operating skills:")
    lines.extend([f"  - {item}" for item in payload.repo_skills])
    lines.append(AGENTS_SYNC_END)
    return "\n".join(lines)


def render_readme_block(payload: OperatingDocsPayload) -> str:
    lines = [
        README_SYNC_START,
        f"- Auto-synced at: `{payload.updated_at}`",
        f"- Current focus: {payload.focus}",
        f"- Last verified workflow status: {payload.verified_status}",
        f"- Biggest operational risk: {payload.risk}",
        "- Validated contour:",
    ]
    lines.extend([f"  - {item}" for item in payload.validated_contour])
    lines.append("- Standalone-owned capabilities:")
    lines.extend([f"  - {item}" for item in payload.owned_capabilities])
    lines.append("- Active repo automations:")
    lines.extend([f"  - {item}" for item in payload.active_automations] or ["  - none detected"])
    lines.append("- Runtime surfaces:")
    lines.extend([f"  - {item}" for item in payload.runtime_surfaces])
    lines.append(README_SYNC_END)
    return "\n".join(lines)


def sync_operating_docs(repo_root: Path) -> dict[Path, str]:
    payload = build_payload(repo_root)
    agents_path = repo_root / "AGENTS.md"
    readme_path = repo_root / "README.md"
    agents_text = _replace_block(_read(agents_path), AGENTS_SYNC_START, AGENTS_SYNC_END, render_agents_block(payload))
    readme_text = _replace_block(_read(readme_path), README_SYNC_START, README_SYNC_END, render_readme_block(payload))
    return {
        agents_path: agents_text,
        readme_path: readme_text,
    }
