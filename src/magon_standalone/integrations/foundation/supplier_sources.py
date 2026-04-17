from __future__ import annotations

import json
from pathlib import Path

from .base import IntegrationResult, SupplierSourceAdapter, SupplierSourcePullResult


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


class FixtureSupplierSourceAdapter(SupplierSourceAdapter):
    adapter_name = "fixture_json"

    def health(self) -> IntegrationResult:
        fixture_path = _repo_root() / "tests" / "fixtures" / "vn_suppliers_raw.json"
        return IntegrationResult(
            ok=fixture_path.exists(),
            adapter=self.adapter_name,
            detail="fixture_ready" if fixture_path.exists() else "fixture_missing",
            payload={"fixture_path": str(fixture_path)},
        )

    def pull(self, config: dict | None = None) -> SupplierSourcePullResult:
        actual_config = config or {}
        fixture_path = Path(actual_config.get("fixture_path") or (_repo_root() / "tests" / "fixtures" / "vn_suppliers_raw.json"))
        source_label = str(actual_config.get("source_label") or "fixture_vn_suppliers")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        # RU: Adapter отдаёт только сырой слой; нормализация и dedup живут выше, в foundation-сервисе.
        return SupplierSourcePullResult(adapter=self.adapter_name, source_label=source_label, records=list(payload))


_ADAPTERS: dict[str, SupplierSourceAdapter] = {
    FixtureSupplierSourceAdapter.adapter_name: FixtureSupplierSourceAdapter(),
}


def list_supplier_source_adapters() -> list[SupplierSourceAdapter]:
    return list(_ADAPTERS.values())


def get_supplier_source_adapter(adapter_key: str) -> SupplierSourceAdapter:
    adapter = _ADAPTERS.get(adapter_key)
    if adapter is None:
        raise KeyError(adapter_key)
    return adapter
