#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from magon_standalone.supplier_intelligence.api import SupplierIntelligenceApiServer, SupplierIntelligenceApiService


def main() -> int:
    parser = argparse.ArgumentParser(description='Run MagonOS Standalone API')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8091)
    parser.add_argument('--db-path', default=str(REPO_ROOT / 'data' / 'supplier_intelligence.sqlite3'))
    parser.add_argument('--default-query', default='printing packaging vietnam')
    parser.add_argument('--default-country', default='VN')
    parser.add_argument('--integration-token', default=os.environ.get('MAGON_STANDALONE_INTEGRATION_TOKEN'))
    args = parser.parse_args()

    service = SupplierIntelligenceApiService(
        db_path=args.db_path,
        default_query=args.default_query,
        default_country=args.default_country,
        integration_token=args.integration_token,
    )
    server = SupplierIntelligenceApiServer(service, host=args.host, port=args.port)
    print(f'MagonOS Standalone API running at {server.base_url}')
    print(f'DB: {Path(args.db_path).resolve()}')
    server.serve_forever()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
