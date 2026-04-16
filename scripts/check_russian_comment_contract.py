#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from magon_standalone.russian_comment_contract import find_missing_ru_comment_files


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    # RU: Контракт проверяем только по staged файлам, иначе hook будет врать про то, что реально уйдёт в commit.
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMRT"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    missing = find_missing_ru_comment_files(repo_root, staged)
    if not missing:
        return 0

    # RU: Сообщение ошибки должно сразу показывать разработчику точную форму допустимого пояснения.
    print("Russian comment contract failed.", file=sys.stderr)
    print("Add at least one added comment/docstring line with `RU:` and Cyrillic text in each changed code file:", file=sys.stderr)
    for path in missing:
        print(f"- {path}", file=sys.stderr)
    print("Example markers: `# RU: ...`, `// RU: ...`, `/* RU: ... */`", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
