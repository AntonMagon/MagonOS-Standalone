#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from magon_standalone.repo_workflow import FinalizeRecord, update_project_memory


def _git_branch(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _run_verifications(repo_root: Path, commands: list[str]) -> list[str]:
    verified: list[str] = []
    for command in commands:
        completed = subprocess.run(command, cwd=repo_root, shell=True)
        if completed.returncode != 0:
            raise RuntimeError(f"verification_failed:{command}")
        verified.append(f"PASS `{command}`")
    return verified


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize a substantial repo task and persist it to project memory.")
    parser.add_argument("--summary", required=True, help="Short summary of the completed task.")
    parser.add_argument("--changed", action="append", required=True, help="Changed file or changed area. Repeat for multiple items.")
    parser.add_argument("--verify", action="append", default=[], help="Verification command. Repeat for multiple commands.")
    parser.add_argument("--risk", default="no additional risk recorded", help="Biggest remaining risk or constraint.")
    parser.add_argument("--focus", default="", help="Current active focus after this task. Defaults to the summary.")
    parser.add_argument(
        "--memory-path",
        default=".codex/project-memory.md",
        help="Project memory file path relative to the repo root.",
    )
    parser.add_argument("--skip-verify", action="store_true", help="Skip verification commands.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    memory_path = repo_root / args.memory_path

    if not memory_path.is_file():
        print(f"finalize-task: missing project memory file {memory_path}", file=sys.stderr)
        return 1

    try:
        verified = ["SKIPPED"] if args.skip_verify else _run_verifications(repo_root, args.verify)
        branch = _git_branch(repo_root)
        timestamp_label = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
        focus = args.focus or args.summary
        record = FinalizeRecord(
            timestamp_label=timestamp_label,
            branch=branch,
            summary=args.summary,
            changed=args.changed,
            verified=verified,
            risk=args.risk,
            focus=focus,
        )
        updated = update_project_memory(memory_path.read_text(encoding="utf-8"), record)
        memory_path.write_text(updated, encoding="utf-8")
    except RuntimeError as exc:
        print(f"finalize-task: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"finalize-task: {exc}", file=sys.stderr)
        return 1

    print(f"Updated {memory_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
