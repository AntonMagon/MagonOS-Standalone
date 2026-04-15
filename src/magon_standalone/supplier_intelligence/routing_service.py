"""Initial review-queue assignment from supplier scores.

Runtime role: Maps composite score bands to a starting operator queue.
Inputs: VendorProfileScorePayload rows.
Outputs: ReviewQueueItem rows.
Does not: apply final route outcomes or write queue rows itself.
"""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import ReviewQueueItem, VendorProfileScorePayload
from .interfaces import RoutingService


@dataclass(frozen=True)
class RoutingThresholds:
    auto_review_threshold: float = 0.75
    manual_review_threshold: float = 0.55


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
