"""Initial review-queue assignment and final routing rules from supplier scores.

Runtime role: Maps composite score bands to a starting operator queue.
Inputs: VendorProfileScorePayload rows.
Outputs: ReviewQueueItem rows.
Does not: apply final route outcomes or write queue rows itself.
"""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import ReviewQueueItem, RoutingOutcome, VendorProfileScorePayload
from .interfaces import RoutingService


@dataclass(frozen=True)
class RoutingThresholds:
    auto_review_threshold: float = 0.75
    manual_review_threshold: float = 0.55


@dataclass(frozen=True)
class RoutingRules:
    approved_threshold: float = 0.78
    potential_threshold: float = 0.58
    relevance_min: float = 0.35
    contactability_min: float = 0.30
    duplicate_threshold: float = 0.92


class ReviewQueueRoutingService(RoutingService):
    """Assign an initial operator queue from score thresholds only."""

    def __init__(self, thresholds: RoutingThresholds | None = None):
        self._thresholds = thresholds or RoutingThresholds()

    def route(self, scores: list[VendorProfileScorePayload]) -> list[ReviewQueueItem]:
        """Create review queue items from score bands for unresolved suppliers."""
        queue: list[ReviewQueueItem] = []
        for item in scores:
            composite = item["composite_score"]
            if composite >= self._thresholds.auto_review_threshold:
                queue_name = "qualification_review"
                reason = "High composite score; ready for qualification decision"
                priority = 90
            elif composite >= self._thresholds.manual_review_threshold:
                queue_name = "supplier_review"
                reason = "Mid composite score; manual profile review required"
                priority = 70
            else:
                queue_name = "dedup_review"
                reason = "Low confidence/fit; verify duplicates and evidence"
                priority = 50
            queue.append(
                {
                    "company_key": item["company_key"],
                    "queue_name": queue_name,
                    "priority": priority,
                    "reason": reason,
                    "score": composite,
                }
            )
        return queue


class RuleBasedBusinessFlowEngine:
    """Apply explicit precedence rules for final supplier routing outcomes."""

    def __init__(self, rules: RoutingRules | None = None):
        self.rules = rules or RoutingRules()

    def decide(
        self,
        score: VendorProfileScorePayload,
        has_pending_dedup: bool,
        dedup_confidence: float,
        manual_override: RoutingOutcome | None = None,
    ) -> tuple[RoutingOutcome, str]:
        if manual_override:
            return manual_override, "manual_override"

        if has_pending_dedup and dedup_confidence >= self.rules.duplicate_threshold:
            return "duplicate", "dedup_high_confidence"

        if has_pending_dedup:
            return "needs_manual_review", "dedup_pending_review"

        composite = score["composite_score"]
        if score["relevance_score"] < self.rules.relevance_min:
            return "not_relevant", "low_relevance"

        if score["contactability_score"] < self.rules.contactability_min:
            return "unreachable", "low_contactability"

        if composite >= self.rules.approved_threshold:
            return "approved_supplier", "high_composite_score"

        if composite >= self.rules.potential_threshold:
            return "potential_supplier", "medium_composite_score"

        return "needs_manual_review", "insufficient_confidence"
