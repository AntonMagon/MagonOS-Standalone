"""Portable supplier-intelligence pipeline orchestration.

Runtime role: Runs discovery through queue routing against explicit persistence
ports, without assuming Odoo as the default storage layer.
Inputs: Service dependencies, one composite persistence adapter, query/country.
Outputs: Persisted raw/canonical workflow effects and a compact run summary.
Does not: assemble dependencies, boot Odoo, or own CRM/commercial side effects.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .contracts import DedupDecisionPayload, NormalizedCompanyRecord, ReviewQueueItem, VendorProfileScorePayload
from .interfaces import (
    DeduplicationService,
    DiscoveryService,
    EnrichmentService,
    NormalizationService,
    RoutingService,
    ScoringService,
    SupplierIntelligencePersistence,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupplierPipelineReport:
    """Compact summary of one synchronous supplier pipeline run."""

    raw_count: int
    normalized_count: int
    deduped_count: int
    dedup_decisions: int
    scored_count: int
    queued_count: int


@dataclass
class SupplierIntelligencePipeline:
    """Coordinate one supplier-intelligence pass against explicit persistence ports."""

    discovery: DiscoveryService
    normalization: NormalizationService
    enrichment: EnrichmentService
    deduplication: DeduplicationService
    scoring: ScoringService
    routing: RoutingService
    repository: SupplierIntelligencePersistence

    def run(self, query: str, country_code: str = "VN") -> SupplierPipelineReport:
        """Run one full synchronous pipeline pass for a query/country pair."""
        LOGGER.info("pipeline.start query=%s country_code=%s", query, country_code)

        raw_records = self.discovery.discover(query=query, country_code=country_code)
        self.repository.save_raw_records(raw_records)
        LOGGER.info("pipeline.discovery raw_count=%s", len(raw_records))

        normalized = self.normalization.normalize(raw_records)
        enriched = self.enrichment.enrich(normalized)
        LOGGER.info("pipeline.normalize normalized_count=%s", len(enriched))

        deduped, dedup_decisions = self.deduplication.deduplicate(enriched)
        LOGGER.info("pipeline.dedup deduped_count=%s decisions=%s", len(deduped), len(dedup_decisions))

        scores = self.scoring.score(deduped)
        queued = self.routing.route(scores)

        company_ids = self.repository.upsert_companies(deduped)
        self.repository.save_vendor_scores(scores, company_ids)
        self.repository.save_dedup_decisions(dedup_decisions, company_ids)
        queued_count = self.repository.route_review_queue(queued, company_ids)

        LOGGER.info("pipeline.done scored=%s queued=%s", len(scores), queued_count)
        return SupplierPipelineReport(
            raw_count=len(raw_records),
            normalized_count=len(enriched),
            deduped_count=len(deduped),
            dedup_decisions=len(dedup_decisions),
            scored_count=len(scores),
            queued_count=queued_count,
        )


def snapshot_scores(scores: list[VendorProfileScorePayload]) -> dict[str, float]:
    """Expose score snapshots in a compact, test-friendly shape."""
    return {score["company_key"]: score["composite_score"] for score in scores}


def snapshot_queue(items: list[ReviewQueueItem]) -> dict[str, str]:
    """Expose queue assignment snapshots for verification and reporting."""
    return {item["company_key"]: item["queue_name"] for item in items}


def snapshot_dedup(decisions: list[DedupDecisionPayload]) -> list[tuple[str, str, str]]:
    """Expose dedup decisions without leaking the full payload structure."""
    return [(item.left_company_key, item.right_company_key, item.decision) for item in decisions]


def canonical_keys(records: list[NormalizedCompanyRecord]) -> list[str]:
    """Return canonical keys for lightweight assertions and diagnostics."""
    return [item["canonical_key"] for item in records if item.get("canonical_key")]
