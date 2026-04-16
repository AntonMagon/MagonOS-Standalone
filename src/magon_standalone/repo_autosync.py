"""Repo-local autosync planning and execution helpers."""

from __future__ import annotations

import fcntl
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


WATCH_TRIGGER_NAME = "magonos-repo-auto"
WATCH_PATTERNS = [
    "src/**",
    "scripts/**",
    "tests/**",
    # RU: Perf сценарии входят в source-of-truth, потому что они меняют operating verdict по скорости и не должны выпадать из autosync.
    "perf/**",
    "apps/web/**",
    "skills/**",
    ".githooks/**",
    "docs/current-project-state.md",
    "docs/repo-workflow.md",
    "docs/performance-and-observability.md",
    "docs/ru/README.md",
    "docs/ru/current-project-state.md",
    "docs/ru/repo-workflow.md",
    "docs/ru/code-map.md",
    "docs/ru/performance-and-observability.md",
    ".codex/project-memory.md",
    ".codex/config.toml",
    "Taskfile.yml",
]
WEB_PREFIXES = ("apps/web/",)
IGNORED_OUTPUT_PREFIXES = (
    "AGENTS.md",
    "README.md",
    "docs/ru/visuals/",
    "docs/visuals/",
)
VERIFY_PREFIXES = (
    "src/",
    "scripts/",
    "tests/",
    "perf/",
    ".githooks/",
    "docs/current-project-state.md",
    "docs/repo-workflow.md",
    "docs/performance-and-observability.md",
    "docs/ru/",
    ".codex/project-memory.md",
    ".codex/config.toml",
    "skills/",
    "Taskfile.yml",
    ".watchmanconfig",
)


@dataclass(frozen=True)
class AutoPlan:
    changed_paths: tuple[str, ...]
    sync_root_docs: bool
    sync_visual_map: bool
    verify_mode: str


def normalize_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in paths:
        path = raw.strip()
        if not path:
            continue
        normalized.append(path.lstrip("./"))
    return normalized


def _is_ignored_output(path: str) -> bool:
    if path.startswith(IGNORED_OUTPUT_PREFIXES):
        return True
    if "__pycache__" in path:
        return True
    if ".pyc" in Path(path).name:
        return True
    return False


def build_auto_plan(paths: list[str]) -> AutoPlan:
    original_changed = normalize_paths(paths)
    changed = tuple(path for path in original_changed if not _is_ignored_output(path))
    if not original_changed:
        # RU: В fallback watch-режиме без списка файлов идём по безопасному широкому сценарию.
        return AutoPlan(changed_paths=(), sync_root_docs=True, sync_visual_map=True, verify_mode="base")
    if not changed:
        return AutoPlan(changed_paths=(), sync_root_docs=False, sync_visual_map=False, verify_mode="none")

    verify_mode = "none"
    if any(path.startswith(WEB_PREFIXES) for path in changed):
        verify_mode = "web"
    elif any(path == ".watchmanconfig" or path.startswith(VERIFY_PREFIXES) for path in changed):
        verify_mode = "base"

    return AutoPlan(
        changed_paths=changed,
        sync_root_docs=True,
        sync_visual_map=True,
        verify_mode=verify_mode,
    )


def plan_commands(repo_root: Path, plan: AutoPlan) -> list[list[str]]:
    python_bin = repo_root / ".venv" / "bin" / "python"
    commands: list[list[str]] = []
    if plan.sync_root_docs:
        commands.append([str(python_bin), "scripts/sync_operating_docs.py"])
    if plan.sync_visual_map:
        commands.append([str(python_bin), "scripts/update_project_visual_map.py"])
    if plan.verify_mode == "web":
        commands.append(["./scripts/verify_workflow.sh", "--with-web"])
    elif plan.verify_mode == "base":
        commands.append(["./scripts/verify_workflow.sh"])
    return commands


def run_plan(repo_root: Path, plan: AutoPlan, log_path: Path, lock_path: Path) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        with log_path.open("a", encoding="utf-8") as log_file:
            started = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
            log_file.write(f"\n== autosync {started} ==\n")
            if plan.changed_paths:
                log_file.write("changed:\n")
                for path in plan.changed_paths:
                    log_file.write(f"  - {path}\n")
            else:
                log_file.write("changed:\n  - <watch fallback>\n")
            env = os.environ.copy()
            # RU: Autosync не должен сам плодить __pycache__ в watched paths, иначе Watchman видит это как новое изменение и уходит в loop.
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            for command in plan_commands(repo_root, plan):
                log_file.write(f"$ {' '.join(command)}\n")
                log_file.flush()
                completed = subprocess.run(
                    command,
                    cwd=repo_root,
                    stdout=log_file,
                    stderr=log_file,
                    text=True,
                    env=env,
                )
                if completed.returncode != 0:
                    raise RuntimeError(f"autosync_command_failed:{' '.join(command)}")
            log_file.write("autosync: ok\n")
