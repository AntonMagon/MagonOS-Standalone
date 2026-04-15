"""Supplier scoring framework for the current MVP.

Runtime role: Computes explicit sub-scores and composite score from normalized records.
Inputs: NormalizedCompanyRecord rows.
Outputs: VendorProfileScorePayload rows.
Does not: make final routing decisions or access Odoo models.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .contracts import NormalizedCompanyRecord, VendorProfileScorePayload
from .interfaces import ScoringService


@dataclass(frozen=True)
class ScoringWeights:
    relevance_weight: float = 0.30
    capability_fit_weight: float = 0.25
    contactability_weight: float = 0.20
    freshness_weight: float = 0.10
    trust_weight: float = 0.15


class ConfigurableScoringService(ScoringService):
    """Compute explicit supplier sub-scores and one bounded composite score."""

    def __init__(self, weights: ScoringWeights | None = None):
        self._weights = weights or ScoringWeights()

    def score(self, records: list[NormalizedCompanyRecord]) -> list[VendorProfileScorePayload]:
        """Score normalized records without mutating them or touching persistence."""
        scored: list[VendorProfileScorePayload] = []
        for record in records:
            relevance = self._relevance(record)
            capability_fit = self._capability_fit(record)
            contactability = self._contactability(record)
            freshness = self._freshness(record)
            trust = self._trust(record)
            # Keep the composite formula explicit so routing thresholds can be tuned against visible subscores.
            composite = (
                relevance * self._weights.relevance_weight
                + capability_fit * self._weights.capability_fit_weight
                + contactability * self._weights.contactability_weight
                + freshness * self._weights.freshness_weight
                + trust * self._weights.trust_weight
            )
            scored.append(
                {
                    "company_key": record["canonical_key"],
                    "relevance_score": round(relevance, 4),
                    "capability_fit_score": round(capability_fit, 4),
                    "contactability_score": round(contactability, 4),
                    "freshness_score": round(freshness, 4),
                    "trust_score": round(trust, 4),
                    "composite_score": round(min(max(composite, 0.0), 1.0), 4),
                    "parser_confidence": round(float(record.get("parser_confidence") or 0.0), 4),
                }
            )
        return scored

    @staticmethod
    def _relevance(record: NormalizedCompanyRecord) -> float:
        caps = set(record.get("capabilities") or [])
        if not caps:
            return 0.35
        high_value = {"PACK_CORRUGATED", "LABEL_SELF_ADHESIVE", "PRINT_OFFSET", "PRINT_FLEXO", "WIDE_FORMAT"}
        overlap = len(caps.intersection(high_value))
        return min(0.35 + overlap * 0.18, 1.0)

    @staticmethod
    def _capability_fit(record: NormalizedCompanyRecord) -> float:
        count = len(record.get("capabilities") or [])
        return min(0.2 + (count * 0.2), 1.0)

    @staticmethod
    def _contactability(record: NormalizedCompanyRecord) -> float:
        score = 0.0
        if record.get("canonical_email"):
            score += 0.4
        if record.get("canonical_phone"):
            score += 0.35
        if record.get("website"):
            score += 0.25
        return min(score, 1.0)

    @staticmethod
    def _freshness(record: NormalizedCompanyRecord) -> float:
        # MVP: adapters emit near-real-time values, keep explicit and easy to tune.
        _ = datetime.now(timezone.utc)
        return 0.9 if record.get("provenance") else 0.5

    @staticmethod
    def _trust(record: NormalizedCompanyRecord) -> float:
        parser = float(record.get("parser_confidence") or 0.0)
        source = float(record.get("source_confidence") or 0.0)
        confidence = float(record.get("confidence") or 0.0)
        return min(max((parser * 0.4) + (source * 0.3) + (confidence * 0.3), 0.0), 1.0)
