"""Protocol definitions for runtime service boundaries.

Runtime role: Documents replaceable service contracts without owning runtime assembly.
Inputs: Service implementation type hints.
Outputs: Protocol definitions used by services and tests.
Does not: provide concrete implementations or persistence.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import (
    DedupDecisionPayload,
    DiscoverySeed,
    FeedbackEventPayload,
    FeedbackStatusProjection,
    MatchRoutingInput,
    NormalizedCompanyRecord,
    PageProfile,
    PageSeed,
    RawCompanyRecord,
    ScenarioRouteDecision,
    ReviewQueueItem,
    SupplierScore,
    RoutingDecisionResult,
    RoutingOutcome,
    VendorProfileScorePayload,
    WorkforceEstimateInput,
    WorkforceEstimateResult,
)


class SourceAdapter(Protocol):
    source_type: str

    def discover(self, seed: DiscoverySeed) -> list[RawCompanyRecord]:
        ...


class DiscoveryService(Protocol):
    def discover(self, query: str, country_code: str) -> list[RawCompanyRecord]:
        ...


class PageSeedProvider(Protocol):
    def discover_seeds(self, query: str, country_code: str) -> list[PageSeed]:
        ...


class PageProfiler(Protocol):
    def profile(self, seed: PageSeed, html: str, status_code: int = 200) -> PageProfile:
        ...


class ScenarioRouter(Protocol):
    def route(self, seed: PageSeed, profile: PageProfile) -> ScenarioRouteDecision:
        ...


class NormalizationService(Protocol):
    def normalize(self, records: list[RawCompanyRecord]) -> list[NormalizedCompanyRecord]:
        ...


class EnrichmentService(Protocol):
    def enrich(self, records: list[NormalizedCompanyRecord]) -> list[NormalizedCompanyRecord]:
        ...


class DeduplicationService(Protocol):
    def deduplicate(self, records: list[NormalizedCompanyRecord]) -> tuple[list[NormalizedCompanyRecord], list[DedupDecisionPayload]]:
        ...


class ScoringService(Protocol):
    def score(self, records: list[NormalizedCompanyRecord]) -> list[VendorProfileScorePayload]:
        ...


class RoutingService(Protocol):
    def route(self, scores: list[VendorProfileScorePayload]) -> list[ReviewQueueItem]:
        ...


@runtime_checkable
class RawRecordStore(Protocol):
    def save_raw_records(self, records: list[RawCompanyRecord]) -> list[int]:
        ...


@runtime_checkable
class CanonicalCompanyStore(Protocol):
    def upsert_companies(self, records: list[NormalizedCompanyRecord]) -> dict[str, int]:
        ...


@runtime_checkable
class ScoreStore(Protocol):
    def save_vendor_scores(self, scores: list[VendorProfileScorePayload], company_ids: dict[str, int]) -> None:
        ...


@runtime_checkable
class DedupDecisionStore(Protocol):
    def save_dedup_decisions(self, decisions: list[DedupDecisionPayload], company_ids: dict[str, int]) -> None:
        ...


@runtime_checkable
class ReviewQueueStore(Protocol):
    def route_review_queue(self, items: list[ReviewQueueItem], company_ids: dict[str, int]) -> int:
        ...


@runtime_checkable
class FeedbackEventStore(Protocol):
    def save_feedback_events(self, events: list[FeedbackEventPayload]) -> int:
        ...

    def list_feedback_events(self, limit: int = 100, offset: int = 0) -> list[dict]:
        ...

    def list_feedback_status(self, limit: int = 100, offset: int = 0) -> list[FeedbackStatusProjection]:
        ...

    def get_feedback_status(self, source_key: str) -> FeedbackStatusProjection | None:
        ...


@runtime_checkable
class SupplierIntelligencePersistence(
    RawRecordStore,
    CanonicalCompanyStore,
    ScoreStore,
    DedupDecisionStore,
    ReviewQueueStore,
    Protocol,
):
    """Composite persistence boundary for the extracted supplier-intelligence slice."""


@runtime_checkable
class RoutingDecisionStore(Protocol):
    def apply_routing_decision(
        self,
        company_key: str,
        outcome: RoutingOutcome,
        reason_code: str,
        evidence_refs: list[str],
        notes: str,
        manual_override: bool,
    ) -> RoutingDecisionResult:
        ...


class PipelineRepository(SupplierIntelligencePersistence, RoutingDecisionStore, Protocol):
    """Backward-compatible composite protocol used by existing addon code."""


class WorkforceEstimationService(Protocol):
    def estimate(self, estimation_input: WorkforceEstimateInput) -> WorkforceEstimateResult:
        ...


class CommunicationAgentService(Protocol):
    def draft_response(self, request_id: int, prompt: str) -> str:
        ...


class LegacyRoutingService(Protocol):
    def route(self, routing_inputs: list[MatchRoutingInput]) -> None:
        ...


class LegacyScoringService(Protocol):
    def score(self, records: list[NormalizedCompanyRecord]) -> list[SupplierScore]:
        ...


class QueueTransitionService(Protocol):
    def transition(self, queue_id: int, target_status: str, reason_code: str, notes: str = "", allow_reprocess: bool = False) -> bool:
        ...


class QualificationDecisionService(Protocol):
    def decide(
        self,
        company_key: str,
        reason_code: str = "",
        evidence_refs: list[str] | None = None,
        notes: str = "",
        manual_override: bool = False,
        forced_outcome: RoutingOutcome | None = None,
    ) -> RoutingDecisionResult:
        ...
