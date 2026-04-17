# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class IntegrationResult:
    ok: bool
    adapter: str
    detail: str
    payload: dict | None = None


@dataclass(slots=True)
class SupplierSourcePullResult:
    adapter: str
    source_label: str
    records: list[dict] = field(default_factory=list)


class IntegrationAdapter(Protocol):
    adapter_name: str

    def health(self) -> IntegrationResult:
        ...


class SupplierSourceAdapter(Protocol):
    adapter_name: str

    def health(self) -> IntegrationResult:
        ...

    def pull(self, config: dict | None = None) -> SupplierSourcePullResult:
        ...
