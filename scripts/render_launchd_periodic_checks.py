#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# RU: Render-script должен поднимать repo src сам, иначе launchd installer сломается вне editable-shell контекста.
from magon_standalone.launchd_periodic_checks import render_launch_agent


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the MagonOS launchd agent for periodic checks.")
    parser.add_argument("--interval", type=int, default=1800, help="LaunchAgent StartInterval in seconds.")
    parser.add_argument("--label", default="com.magonos.periodic-checks", help="LaunchAgent label.")
    parser.add_argument("--output", required=True, help="Target plist path.")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_launch_agent(REPO_ROOT, args.interval, args.label), encoding="utf-8")
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
