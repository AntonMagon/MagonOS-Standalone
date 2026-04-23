#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# RU: Render-script держим self-contained, чтобы installer работал и вне editable-shell, если repo запускают напрямую.
from magon_standalone.launchd_launcher_watchdog import render_launcher_watchdog_agent


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the MagonOS launchd agent for launcher watchdog.")
    parser.add_argument("--interval", type=int, default=3600, help="LaunchAgent StartInterval in seconds.")
    parser.add_argument("--label", default="com.magonos.launcher-watchdog", help="LaunchAgent label.")
    parser.add_argument("--output", required=True, help="Target plist path.")
    # RU: launchd-root и helper script передаём явно, чтобы installer мог увести agent из Desktop repo в домашний support-path без скрытых путей.
    parser.add_argument("--launchd-root", help="LaunchAgent working/log directory outside the repo.")
    parser.add_argument("--program", help="Helper script path used by LaunchAgent ProgramArguments.")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    launchd_root = Path(args.launchd_root).expanduser() if args.launchd_root else None
    program_path = Path(args.program).expanduser() if args.program else None
    output_path.write_text(
        render_launcher_watchdog_agent(REPO_ROOT, args.interval, args.label, launchd_root=launchd_root, program_path=program_path),
        encoding="utf-8",
    )
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
