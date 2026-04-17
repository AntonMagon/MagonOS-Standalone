# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from starlette.middleware.wsgi import WSGIMiddleware

from magon_standalone.supplier_intelligence.api import SupplierIntelligenceApiService, create_wsgi_app

from .settings import FoundationSettings


def create_legacy_mount(settings: FoundationSettings) -> WSGIMiddleware:
    service = SupplierIntelligenceApiService(
        db_path=settings.legacy_db_path,
        default_query=settings.legacy_default_query,
        default_country=settings.legacy_default_country,
        integration_token=settings.legacy_integration_token or None,
    )
    return WSGIMiddleware(create_wsgi_app(service))
