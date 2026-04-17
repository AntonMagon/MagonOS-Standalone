# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from dataclasses import dataclass

from .base import IntegrationResult


@dataclass(slots=True)
class NotificationAdapter:
    adapter_name: str = "notifications"
    transport: str = "noop"

    def health(self) -> IntegrationResult:
        return IntegrationResult(ok=True, adapter=self.adapter_name, detail=f"Notification adapter configured with transport={self.transport}.")
