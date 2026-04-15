#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from magon_standalone.supplier_intelligence.sqlite_persistence import SqliteSupplierIntelligenceStore


TABLES = {
    'raw-records': 'list_raw_records',
    'companies': 'list_companies',
    'scores': 'list_scores',
    'dedup-decisions': 'list_dedup_decisions',
    'review-queue': 'list_review_queue',
    'feedback-events': 'list_feedback_events',
    'feedback-status': 'list_feedback_status',
}


def main() -> int:
    parser = argparse.ArgumentParser(description='Inspect MagonOS Standalone persisted results')
    parser.add_argument('--db-path', default=str(REPO_ROOT / 'data' / 'supplier_intelligence.sqlite3'))
    parser.add_argument('--table', choices=sorted(TABLES.keys()), required=True)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--offset', type=int, default=0)
    args = parser.parse_args()

    store = SqliteSupplierIntelligenceStore(args.db_path)
    method = getattr(store, TABLES[args.table])
    rows = method(limit=args.limit, offset=args.offset)
    print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
