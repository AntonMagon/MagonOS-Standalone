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


def _env(name: str, fallback: str, legacy: str | None = None) -> str:
    value = os.environ.get(name)
    if value:
        return value
    if legacy:
        legacy_value = os.environ.get(legacy)
        if legacy_value:
            return legacy_value
    return fallback


def main() -> int:
    parser = argparse.ArgumentParser(description='Run MagonOS Standalone API')
    parser.add_argument('--host', default=_env('MAGON_STANDALONE_HOST', '127.0.0.1', 'SUPPLIER_INTELLIGENCE_API_HOST'))
    parser.add_argument('--port', type=int, default=int(_env('MAGON_STANDALONE_PORT', '8091', 'SUPPLIER_INTELLIGENCE_API_PORT')))
    parser.add_argument('--db-path', default=_env('MAGON_STANDALONE_DB_PATH', str(REPO_ROOT / 'data' / 'platform.sqlite3'), 'SUPPLIER_INTELLIGENCE_DB_PATH'))
    parser.add_argument('--default-query', default=_env('MAGON_STANDALONE_DEFAULT_QUERY', 'printing packaging vietnam'))
    parser.add_argument('--default-country', default=_env('MAGON_STANDALONE_DEFAULT_COUNTRY', 'VN'))
    parser.add_argument('--integration-token', default=os.environ.get('MAGON_STANDALONE_INTEGRATION_TOKEN') or os.environ.get('SUPPLIER_INTELLIGENCE_SYNC_TOKEN'))
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
