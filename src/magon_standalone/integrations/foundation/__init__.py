# RU: Пакет integrations.foundation держим lazy-aware, чтобы supplier parsing мог тянуть LLM/runtime submodules без циклического захода во весь foundation app.
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import IntegrationAdapter, SupplierSourceAdapter
from .legacy_runtime import LegacyRuntimeAdapter
from .notifications import NotificationAdapter

if TYPE_CHECKING:
    from .storage import StorageAdapter


def get_storage_adapter(*args: Any, **kwargs: Any):
    from .storage import get_storage_adapter as _get_storage_adapter

    return _get_storage_adapter(*args, **kwargs)


def get_supplier_source_adapter(*args: Any, **kwargs: Any):
    from .supplier_sources import get_supplier_source_adapter as _get_supplier_source_adapter

    return _get_supplier_source_adapter(*args, **kwargs)


def list_supplier_source_adapters(*args: Any, **kwargs: Any):
    from .supplier_sources import list_supplier_source_adapters as _list_supplier_source_adapters

    return _list_supplier_source_adapters(*args, **kwargs)

__all__ = [
    "IntegrationAdapter",
    "SupplierSourceAdapter",
    "LegacyRuntimeAdapter",
    "NotificationAdapter",
    "get_storage_adapter",
    "get_supplier_source_adapter",
    "list_supplier_source_adapters",
]
