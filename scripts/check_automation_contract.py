#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from magon_standalone.automation_contract import scan_automation_contract


def main() -> int:
    automation_root = Path.home() / ".codex" / "automations"
    # RU: Этот guard валидирует именно живые Codex automation, а не repo snapshots, чтобы расписания не уплывали мимо рабочего контекста проекта.
    issues = scan_automation_contract(automation_root)
    if issues:
        for issue in issues:
            print(f"check-automation-contract: {issue}")
        return 1

    print("Automation contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
