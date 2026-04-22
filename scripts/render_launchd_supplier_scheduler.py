#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

import sys

if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from magon_standalone.launchd_supplier_scheduler import render_supplier_scheduler_agent


def main() -> int:
    # RU: Plist генерируем из одного места, чтобы launchd-конфиг scheduler не расходился с путями активного репозитория.
    parser = argparse.ArgumentParser(description="Render the MagonOS launchd agent for the supplier scheduler.")
    parser.add_argument("--interval", type=int, default=3600, help="LaunchAgent StartInterval in seconds.")
    parser.add_argument("--label", default="com.magonos.supplier-scheduler", help="LaunchAgent label.")
    parser.add_argument("--output", required=True, help="Target plist path.")
    args = parser.parse_args()

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_supplier_scheduler_agent(REPO_ROOT, args.interval, args.label), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
