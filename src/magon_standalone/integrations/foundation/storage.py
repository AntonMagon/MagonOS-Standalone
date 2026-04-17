# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...foundation.settings import FoundationSettings


@dataclass(slots=True)
class StoredObject:
    backend: str
    storage_key: str
    absolute_path: str
    byte_size: int


class StorageAdapter:
    def save_bytes(self, *, storage_key: str, content: bytes) -> StoredObject:  # pragma: no cover - interface only
        raise NotImplementedError

    def read_bytes(self, *, storage_key: str) -> bytes:  # pragma: no cover - interface only
        raise NotImplementedError

    def absolute_path(self, *, storage_key: str) -> str:  # pragma: no cover - interface only
        raise NotImplementedError


class LocalFileStorageAdapter(StorageAdapter):
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, *, storage_key: str, content: bytes) -> StoredObject:
        target = self.root_dir / storage_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredObject(backend="local", storage_key=storage_key, absolute_path=str(target), byte_size=len(content))

    def read_bytes(self, *, storage_key: str) -> bytes:
        return (self.root_dir / storage_key).read_bytes()

    def absolute_path(self, *, storage_key: str) -> str:
        return str(self.root_dir / storage_key)


class ObjectStorageReadyAdapter(StorageAdapter):
    def __init__(self, _: FoundationSettings):
        self.backend = "object"

    def save_bytes(self, *, storage_key: str, content: bytes) -> StoredObject:  # pragma: no cover - runtime guard
        raise NotImplementedError("object_storage_backend_not_configured")

    def read_bytes(self, *, storage_key: str) -> bytes:  # pragma: no cover - runtime guard
        raise NotImplementedError("object_storage_backend_not_configured")

    def absolute_path(self, *, storage_key: str) -> str:  # pragma: no cover - runtime guard
        raise NotImplementedError("object_storage_backend_not_configured")


def get_storage_adapter(settings: FoundationSettings) -> StorageAdapter:
    if settings.storage_backend == "local":
        return LocalFileStorageAdapter(settings.storage_local_root)
    if settings.storage_backend == "object":
        return ObjectStorageReadyAdapter(settings)
    raise RuntimeError(f"unsupported_storage_backend:{settings.storage_backend}")
