# RU: Файл входит в проверенный контур первой волны.
from .base import IntegrationAdapter, SupplierSourceAdapter
from .legacy_runtime import LegacyRuntimeAdapter
from .notifications import NotificationAdapter
from .storage import StorageAdapter, get_storage_adapter
from .supplier_sources import get_supplier_source_adapter, list_supplier_source_adapters

__all__ = [
    "IntegrationAdapter",
    "SupplierSourceAdapter",
    "LegacyRuntimeAdapter",
    "NotificationAdapter",
    "StorageAdapter",
    "get_storage_adapter",
    "get_supplier_source_adapter",
    "list_supplier_source_adapters",
]
