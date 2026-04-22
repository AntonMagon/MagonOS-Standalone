#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

import sys

if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from magon_standalone.foundation.db import create_session_factory, session_scope
from magon_standalone.foundation.supplier_scheduler import enqueue_due_supplier_sources
from magon_standalone.foundation.settings import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the periodic standalone supplier parser/classifier scheduler.")
    parser.add_argument("--mode", default="manual", choices=["manual", "launchd"], help="Execution mode label.")
    args = parser.parse_args()

    settings = load_settings()
    session_factory = create_session_factory(settings)
    with session_scope(session_factory) as session:
        results = enqueue_due_supplier_sources(session)
    payload = {
        "mode": args.mode,
        "scheduled_count": sum(1 for item in results if item.get("scheduled")),
        "results": results,
    }
    # RU: Scheduler печатает explainable JSON, чтобы launchd/operator могли быстро увидеть, что именно было поставлено в очередь и почему остальное пропущено.
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
