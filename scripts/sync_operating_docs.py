#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from magon_standalone.operating_docs_sync import sync_operating_docs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync repo-root AGENTS.md and README.md from canonical repo state.")
    parser.add_argument("--check", action="store_true", help="Fail if AGENTS.md or README.md are out of sync.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    rendered = sync_operating_docs(repo_root)
    drifted: list[Path] = []
    for path, new_text in rendered.items():
        current_text = path.read_text(encoding="utf-8")
        if current_text != new_text:
            drifted.append(path)
            if not args.check:
                path.write_text(new_text, encoding="utf-8")

    if args.check and drifted:
        # RU: Корневые operating docs не должны отставать от project-memory, skills и automation state.
        for path in drifted:
            print(f"sync-operating-docs: out of sync {path.relative_to(repo_root)}", file=sys.stderr)
        return 1

    for path in drifted:
        print(f"Updated {path.relative_to(repo_root)}")
    if not drifted:
        print("Operating docs already in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
