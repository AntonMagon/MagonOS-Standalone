#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from magon_standalone.repo_autosync import build_auto_plan, plan_commands, run_plan


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repo autosync actions for changed paths.")
    parser.add_argument("paths", nargs="*", help="Changed repo-relative paths, usually appended by Watchman.")
    parser.add_argument("--all", action="store_true", help="Run the fallback full autosync plan even without changed paths.")
    parser.add_argument("--dry-run", action="store_true", help="Print the computed plan and exit.")
    parser.add_argument(
        "--log-path",
        default=".cache/repo-autosync.log",
        help="Autosync log file path relative to repo root.",
    )
    parser.add_argument(
        "--lock-path",
        default=".cache/repo-autosync.lock",
        help="Autosync lock file path relative to repo root.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    changed_paths = [] if args.all else args.paths
    plan = build_auto_plan(changed_paths)

    if args.dry_run:
        print(f"changed_paths={list(plan.changed_paths)}")
        print(f"sync_root_docs={plan.sync_root_docs}")
        print(f"sync_visual_map={plan.sync_visual_map}")
        print(f"verify_mode={plan.verify_mode}")
        return 0

    if not plan_commands(repo_root, plan):
        print("repo autosync skipped")
        return 0

    try:
        # RU: Autosync должен оставаться repo-native: запускаем те же скрипты, которые уже признаются каноническими guards и verification.
        run_plan(repo_root, plan, repo_root / args.log_path, repo_root / args.lock_path)
    except RuntimeError as exc:
        print(f"run-repo-autosync: {exc}", file=sys.stderr)
        return 1

    print("repo autosync completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
