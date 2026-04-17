"""Validation helpers for Codex automation contract."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


AUTOMATION_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){1,4}$")
ALLOWED_HOURLY_RRULE = re.compile(r"^FREQ=HOURLY;INTERVAL=\d+$")
ALLOWED_WEEKLY_RRULE = re.compile(
    r"^FREQ=WEEKLY;BYDAY=[A-Z]{2}(?:,[A-Z]{2})*;BYHOUR=\d{1,2};BYMINUTE=\d{1,2}$"
)
AUTOMATION_CONTEXT_FRAGMENT = "skills/automation-context-guard/SKILL.md"
EXPECTED_REPO_CWD = "/Users/anton/Desktop/MagonOS-Standalone"


@dataclass(frozen=True)
class AutomationIssue:
    path: str
    message: str

    def render(self) -> str:
        return f"{self.path}: {self.message}"


def _valid_rrule(value: str) -> bool:
    return bool(ALLOWED_HOURLY_RRULE.match(value) or ALLOWED_WEEKLY_RRULE.match(value))


def parse_simple_toml(text: str) -> dict[str, object]:
    data: dict[str, object] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        try:
            # RU: Нам не нужен полноценный TOML parser; для нашего fixed-shape automation.toml хватает безопасного literal_eval на строках, числах и списках.
            data[key] = ast.literal_eval(value)
        except Exception:
            data[key] = value.strip('"')
    return data


def validate_automation_file(automation_file: Path) -> list[AutomationIssue]:
    issues: list[AutomationIssue] = []
    relative = automation_file.relative_to(automation_file.parent.parent).as_posix()
    data = parse_simple_toml(automation_file.read_text(encoding="utf-8"))
    folder_id = automation_file.parent.name

    automation_id = str(data.get("id") or "")
    if automation_id != folder_id:
        issues.append(AutomationIssue(relative, f"id `{automation_id}` must match folder `{folder_id}`"))
    if not AUTOMATION_ID_PATTERN.match(automation_id):
        issues.append(AutomationIssue(relative, "automation id must be lowercase kebab-case with 2-5 tokens"))

    if data.get("kind") != "cron":
        issues.append(AutomationIssue(relative, "automation kind must stay `cron`"))

    name = str(data.get("name") or "")
    if not name or name != name.strip():
        issues.append(AutomationIssue(relative, "automation name must be non-empty and trimmed"))

    prompt = str(data.get("prompt") or "")
    # RU: Все repo automation должны явно тянуть общий meta-skill, иначе они снова начнут читать проект по-разному и жить от разных кусков контекста.
    if AUTOMATION_CONTEXT_FRAGMENT not in prompt:
        issues.append(AutomationIssue(relative, "prompt must reference automation-context-guard"))

    cwds = data.get("cwds")
    if not isinstance(cwds, list) or cwds != [EXPECTED_REPO_CWD]:
        issues.append(AutomationIssue(relative, "cwds must contain exactly the standalone repo root"))

    if data.get("execution_environment") != "local":
        issues.append(AutomationIssue(relative, "execution_environment must stay `local`"))

    model = str(data.get("model") or "")
    if not model.startswith("gpt-5"):
        issues.append(AutomationIssue(relative, "model must stay on a gpt-5 family runtime"))

    rrule = str(data.get("rrule") or "")
    if not _valid_rrule(rrule):
        issues.append(AutomationIssue(relative, "rrule must stay within supported hourly or weekly cron shapes"))

    return issues


def scan_automation_contract(automation_root: Path) -> list[str]:
    issues: list[str] = []
    for automation_file in sorted(automation_root.glob("*/automation.toml")):
        for issue in validate_automation_file(automation_file):
            issues.append(issue.render())
    return issues
