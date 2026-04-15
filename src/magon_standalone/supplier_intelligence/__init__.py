"""Standalone supplier-intelligence package extracted from MagonOS.

This package is intentionally Odoo-free for core runtime and persistence.
Live crawling helpers remain available behind optional dependencies.
"""

from .api import SupplierIntelligenceApiServer, SupplierIntelligenceApiService, create_wsgi_app
from .runtime import build_standalone_pipeline, run_standalone_pipeline
from .sqlite_persistence import SqliteSupplierIntelligenceStore

__all__ = [
    "SupplierIntelligenceApiServer",
    "SupplierIntelligenceApiService",
    "SqliteSupplierIntelligenceStore",
    "build_standalone_pipeline",
    "create_wsgi_app",
    "run_standalone_pipeline",
]
