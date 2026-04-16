"""Utilities for enforcing Russian explanatory comments in staged code changes."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_RU_MARKER_RE = re.compile(r"RU:\s*.+")


def is_code_file(path: str) -> bool:
    # RU: Здесь описываем именно те зоны репо, где изменение кода должно сопровождаться русским пояснением.
    suffix = Path(path).suffix
    if path.startswith(".githooks/"):
        return True
    if path.startswith("scripts/") and suffix in {".py", ".sh"}:
        return True
    if path.startswith("src/") and suffix == ".py":
        return True
    if path.startswith("tests/") and suffix == ".py":
        return True
    if path.startswith("apps/web/") and suffix in {".ts", ".tsx", ".js", ".jsx"}:
        return True
    return False


def added_ru_comment_lines(diff_text: str) -> list[str]:
    matches: list[str] = []
    for line in diff_text.splitlines():
        if not line.startswith("+"):
            continue
        if line.startswith("+++"):
            continue
        content = line[1:]
        if "RU:" not in content:
            continue
        if _RU_MARKER_RE.search(content) and _CYRILLIC_RE.search(content):
            matches.append(content)
    return matches


def staged_diff(repo_root: Path, path: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--", path],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def find_missing_ru_comment_files(
    repo_root: Path,
    staged_files: list[str],
    diff_provider: Callable[[Path, str], str] | None = None,
) -> list[str]:
    # RU: Проверяем staged diff, а не рабочее дерево, потому что commit-guard должен смотреть на реальный commit payload.
    diff_provider = diff_provider or staged_diff
    missing: list[str] = []
    for path in staged_files:
        if not is_code_file(path):
            continue
        diff_text = diff_provider(repo_root, path)
        if added_ru_comment_lines(diff_text):
            continue
        missing.append(path)
    return missing
