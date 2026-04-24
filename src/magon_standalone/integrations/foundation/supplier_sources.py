from __future__ import annotations

import json
from pathlib import Path

from .base import IntegrationResult, SupplierSourceAdapter, SupplierSourcePullResult


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _run_live_discovery(config: dict | None = None) -> list[dict]:
    actual_config = config or {}
    query = str(actual_config.get("query") or "printing packaging vietnam")
    country = str(actual_config.get("country") or "VN")
    from magon_standalone.supplier_intelligence.scenario_config import ScenarioConfig
    from magon_standalone.supplier_intelligence.scenario_discovery_service import ScenarioDrivenDiscoveryService
    from magon_standalone.supplier_intelligence.live_runtime import probe_live_runtime

    scenario_config = ScenarioConfig.load()
    # RU: Live adapter не должен притворяться готовым только по конфигу; readiness обязана проверять реальный browser/runtime before discovery.
    readiness = probe_live_runtime(scenario_config, force_refresh=True)
    if not readiness.ok:
        raise RuntimeError(f"live_runtime_not_ready:{readiness.detail}")
    discovery = ScenarioDrivenDiscoveryService(scenario_config)
    return list(discovery.discover(query=query, country_code=country))


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
        forced_error = str(actual_config.get("force_error") or "").strip()
        if forced_error:
            # RU: Детерминированный сбой адаптера нужен для проверяемого retry/failure контура, а не для "магических" моков вне системы.
            raise RuntimeError(forced_error)
        fixture_path = Path(actual_config.get("fixture_path") or (_repo_root() / "tests" / "fixtures" / "vn_suppliers_raw.json"))
        source_label = str(actual_config.get("source_label") or "fixture_vn_suppliers")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        # RU: Adapter отдаёт только сырой слой; нормализация и dedup живут выше, в foundation-сервисе.
        return SupplierSourcePullResult(adapter=self.adapter_name, source_label=source_label, records=list(payload))


class LiveParsingSupplierSourceAdapter(SupplierSourceAdapter):
    adapter_name = "scenario_live"

    def health(self) -> IntegrationResult:
        try:
            from magon_standalone.supplier_intelligence.scenario_config import ScenarioConfig
            from magon_standalone.supplier_intelligence.live_runtime import probe_live_runtime

            config = ScenarioConfig.load()
            # RU: Health surface должен отражать исполнимость live parsing path, а не просто наличие source adapter registration.
            readiness = probe_live_runtime(config, force_refresh=True)
        except Exception as exc:
            return IntegrationResult(
                ok=False,
                adapter=self.adapter_name,
                detail="live_parsing_unavailable",
                payload={"error": str(exc)[:500]},
            )
        return IntegrationResult(
            ok=readiness.ok,
            adapter=self.adapter_name,
            detail=readiness.detail,
            payload={
                "low_confidence_threshold": config.settings().low_confidence_threshold,
                **(readiness.payload or {}),
            },
        )

    def pull(self, config: dict | None = None) -> SupplierSourcePullResult:
        actual_config = config or {}
        query = str(actual_config.get("query") or "printing packaging vietnam")
        country = str(actual_config.get("country") or "VN")
        source_label = str(actual_config.get("source_label") or f"live_parsing_{country.lower()}")
        records = _run_live_discovery(actual_config)
        # RU: Live parsing adapter отдаёт уже извлечённые raw supplier rows из scenario-discovery, но не берёт на себя foundation-нормализацию.
        return SupplierSourcePullResult(adapter=self.adapter_name, source_label=source_label, records=list(records))


_ADAPTERS: dict[str, SupplierSourceAdapter] = {
    FixtureSupplierSourceAdapter.adapter_name: FixtureSupplierSourceAdapter(),
    LiveParsingSupplierSourceAdapter.adapter_name: LiveParsingSupplierSourceAdapter(),
}


def list_supplier_source_adapters() -> list[SupplierSourceAdapter]:
    return list(_ADAPTERS.values())


def get_supplier_source_adapter(adapter_key: str) -> SupplierSourceAdapter:
    adapter = _ADAPTERS.get(adapter_key)
    if adapter is None:
        raise KeyError(adapter_key)
    return adapter
