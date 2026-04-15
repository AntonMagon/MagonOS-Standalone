"""Standalone runtime assembly for the supplier-intelligence slice."""
from __future__ import annotations

from pathlib import Path

from .deduplication_service import HybridDeduplicationService
from .fixture_discovery import FixtureDiscoveryService
from .normalization_service import BasicEnrichmentService, BasicNormalizationService
from .pipeline import SupplierIntelligencePipeline
from .routing_service import ReviewQueueRoutingService
from .scoring_service import ConfigurableScoringService
from .sqlite_persistence import SqliteSupplierIntelligenceStore


def build_standalone_pipeline(
    db_path: str | Path,
    fixture_path: str | Path | None = None,
) -> tuple[SupplierIntelligencePipeline, SqliteSupplierIntelligenceStore, str]:
    store = SqliteSupplierIntelligenceStore(db_path)
    if fixture_path:
        discovery = FixtureDiscoveryService(fixture_path)
        mode = "fixture"
    else:
        from .scenario_config import ScenarioConfig
        from .scenario_discovery_service import ScenarioDrivenDiscoveryService

        discovery = ScenarioDrivenDiscoveryService(ScenarioConfig.load())
        mode = "live"
    pipeline = SupplierIntelligencePipeline(
        discovery=discovery,
        normalization=BasicNormalizationService(),
        enrichment=BasicEnrichmentService(),
        deduplication=HybridDeduplicationService(),
        scoring=ConfigurableScoringService(),
        routing=ReviewQueueRoutingService(),
        repository=store,
    )
    return pipeline, store, mode


def run_standalone_pipeline(
    db_path: str | Path,
    query: str = "printing packaging vietnam",
    country: str = "VN",
    fixture_path: str | Path | None = None,
) -> dict[str, object]:
    pipeline, store, mode = build_standalone_pipeline(db_path=db_path, fixture_path=fixture_path)
    report = pipeline.run(query=query, country_code=country)
    return {
        "mode": mode,
        "db_path": str(Path(db_path).resolve()),
        "pipeline_report": {
            "raw_count": report.raw_count,
            "normalized_count": report.normalized_count,
            "deduped_count": report.deduped_count,
            "dedup_decisions": report.dedup_decisions,
            "scored_count": report.scored_count,
            "queued_count": report.queued_count,
        },
        "storage_counts": store.snapshot_counts(),
    }
