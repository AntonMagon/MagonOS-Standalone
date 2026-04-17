#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from magon_standalone.skill_naming import scan_skill_names


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    # RU: Этот script нужен как жёсткий repo guard, чтобы новые локальные skills не плодили хаотичные имена и не путали automation layer.
    issues = scan_skill_names(repo_root)
    if issues:
        for issue in issues:
            print(f"check-skill-naming: {issue}")
        return 1

    print("Skill naming contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
