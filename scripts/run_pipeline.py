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

from magon_standalone.supplier_intelligence.runtime import run_standalone_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description='Run MagonOS Standalone supplier pipeline')
    parser.add_argument('--db-path', default=str(REPO_ROOT / 'data' / 'supplier_intelligence.sqlite3'))
    parser.add_argument('--query', default='printing packaging vietnam')
    parser.add_argument('--country', default='VN')
    parser.add_argument('--fixture', default=str(REPO_ROOT / 'tests' / 'fixtures' / 'vn_suppliers_raw.json'))
    args = parser.parse_args()

    fixture = args.fixture or None
    result = run_standalone_pipeline(
        db_path=args.db_path,
        query=args.query,
        country=args.country,
        fixture_path=fixture,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
