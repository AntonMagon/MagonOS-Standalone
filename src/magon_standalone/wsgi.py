from __future__ import annotations

import os
from pathlib import Path

from magon_standalone.supplier_intelligence.api import SupplierIntelligenceApiService, create_wsgi_app


def _env(name: str, fallback: str | None = None, legacy: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    if legacy:
        legacy_value = os.environ.get(legacy)
        if legacy_value:
            return legacy_value
    return fallback


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = str(REPO_ROOT / 'data' / 'platform.sqlite3')

service = SupplierIntelligenceApiService(
    db_path=_env('MAGON_STANDALONE_DB_PATH', DEFAULT_DB, 'SUPPLIER_INTELLIGENCE_DB_PATH') or DEFAULT_DB,
    default_query=_env('MAGON_STANDALONE_DEFAULT_QUERY', 'printing packaging vietnam') or 'printing packaging vietnam',
    default_country=_env('MAGON_STANDALONE_DEFAULT_COUNTRY', 'VN') or 'VN',
    integration_token=_env('MAGON_STANDALONE_INTEGRATION_TOKEN', None, 'SUPPLIER_INTELLIGENCE_SYNC_TOKEN'),
)

app = create_wsgi_app(service)
