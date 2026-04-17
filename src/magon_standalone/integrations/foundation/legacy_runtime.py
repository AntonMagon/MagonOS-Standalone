# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from dataclasses import dataclass

from .base import IntegrationResult


@dataclass(slots=True)
class LegacyRuntimeAdapter:
    adapter_name: str = "legacy_runtime"
    enabled: bool = True

    def health(self) -> IntegrationResult:
        return IntegrationResult(ok=self.enabled, adapter=self.adapter_name, detail="Legacy runtime bridge mounted through dedicated adapter layer.")
