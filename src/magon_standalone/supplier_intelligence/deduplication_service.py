"""Deduplication logic for normalized supplier records.

Runtime role: Combines deterministic and heuristic matching before canonical persistence.
Inputs: Normalized company records.
Outputs: Deduplicated records plus pair-level decisions.
Does not: persist decisions or perform manual review actions.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from difflib import SequenceMatcher

from .contracts import DedupDecisionPayload, NormalizedCompanyRecord
from .interfaces import DeduplicationService


@dataclass(frozen=True)
class DedupConfig:
    deterministic_confidence: float = 0.98
    heuristic_threshold: float = 0.84
    algorithm_version: str = "v1.0"


class HybridDeduplicationService(DeduplicationService):
    """Combine deterministic identity checks with a small heuristic fallback."""

    def __init__(self, config: DedupConfig | None = None):
        self._config = config or DedupConfig()

    def deduplicate(self, records: list[NormalizedCompanyRecord]) -> tuple[list[NormalizedCompanyRecord], list[DedupDecisionPayload]]:
        """Return merged canonical records and explicit pair-level dedup decisions."""
        kept: dict[str, NormalizedCompanyRecord] = {}
        decisions: list[DedupDecisionPayload] = []

        for item in records:
            matched_key = None
            for current_key, current in kept.items():
                signals = self._match_signals(item, current)
                decision, confidence = self._classify(signals)
                if decision == "same_entity":
                    matched_key = current_key
                    pair_fp = self._pair_fingerprint(item["canonical_key"], current["canonical_key"])
                    decisions.append(
                        DedupDecisionPayload(
                            left_company_key=item["canonical_key"],
                            right_company_key=current["canonical_key"],
                            decision=decision,
                            confidence=confidence,
                            pair_fingerprint=pair_fp,
                            match_signals=signals,
                            algorithm_version=self._config.algorithm_version,
                        )
                    )
                    kept[current_key] = self._merge(current, item)
                    break
                if decision == "needs_manual_review":
                    pair_fp = self._pair_fingerprint(item["canonical_key"], current["canonical_key"])
                    decisions.append(
                        DedupDecisionPayload(
                            left_company_key=item["canonical_key"],
                            right_company_key=current["canonical_key"],
                            decision=decision,
                            confidence=confidence,
                            pair_fingerprint=pair_fp,
                            match_signals=signals,
                            algorithm_version=self._config.algorithm_version,
                        )
                    )
            if matched_key is None:
                kept[item["canonical_key"]] = item
        return list(kept.values()), decisions

    def _classify(self, signals: dict) -> tuple[str, float]:
        # Deterministic identity signals win first; heuristic matching is only a fallback for incomplete public data.
        if signals["registration_exact"]:
            return "same_entity", self._config.deterministic_confidence
        deterministic_contact_or_domain = any(
            [
                signals["website_exact"],
                signals["website_domain_overlap"],
                signals["phone_exact"],
                signals["email_exact"],
            ]
        )
        if deterministic_contact_or_domain and (
            signals["name_similarity"] >= 0.55 or signals["address_similarity"] >= 0.70
        ):
            return "same_entity", self._config.deterministic_confidence

        heuristic = (
            0.40 * signals["name_similarity"]
            + 0.20 * signals["address_similarity"]
            + 0.20 * float(signals["alias_overlap"])
            + 0.20 * float(signals["website_domain_overlap"])
        )
        if heuristic >= self._config.heuristic_threshold:
            return "same_entity", round(float(heuristic), 4)
        if heuristic >= 0.65:
            return "needs_manual_review", round(float(heuristic), 4)
        return "different_entity", round(float(heuristic), 4)

    @staticmethod
    def _match_signals(left: NormalizedCompanyRecord, right: NormalizedCompanyRecord) -> dict:
        left_name = left.get("canonical_name") or ""
        right_name = right.get("canonical_name") or ""
        left_addr = left.get("address_text") or ""
        right_addr = right.get("address_text") or ""

        def domain(website: str | None) -> str:
            if not website:
                return ""
            return website.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/")

        left_alias = set((left.get("brand_alias") or "").lower().split())
        right_alias = set((right.get("brand_alias") or "").lower().split())

        return {
            "name_similarity": SequenceMatcher(None, left_name.lower(), right_name.lower()).ratio(),
            "address_similarity": SequenceMatcher(None, left_addr.lower(), right_addr.lower()).ratio(),
            "website_exact": bool(left.get("website") and left.get("website") == right.get("website")),
            "website_domain_overlap": bool(domain(left.get("website")) and domain(left.get("website")) == domain(right.get("website"))),
            "phone_exact": bool(left.get("canonical_phone") and left.get("canonical_phone") == right.get("canonical_phone")),
            "email_exact": bool(left.get("canonical_email") and left.get("canonical_email") == right.get("canonical_email")),
            "registration_exact": bool(left.get("registration_code") and left.get("registration_code") == right.get("registration_code")),
            "alias_overlap": bool(left_alias and right_alias and left_alias.intersection(right_alias)),
        }

    @staticmethod
    def _pair_fingerprint(left_key: str, right_key: str) -> str:
        ordered = sorted([left_key, right_key])
        return hashlib.sha1(f"{ordered[0]}|{ordered[1]}".encode("utf-8")).hexdigest()

    @staticmethod
    def _merge(current: NormalizedCompanyRecord, incoming: NormalizedCompanyRecord) -> NormalizedCompanyRecord:
        merged = dict(current)
        if not merged.get("canonical_email") and incoming.get("canonical_email"):
            merged["canonical_email"] = incoming["canonical_email"]
        if not merged.get("canonical_phone") and incoming.get("canonical_phone"):
            merged["canonical_phone"] = incoming["canonical_phone"]
        merged_caps = list(dict.fromkeys((merged.get("capabilities") or []) + (incoming.get("capabilities") or [])))
        merged["capabilities"] = merged_caps
        merged["confidence"] = max(float(merged.get("confidence") or 0.0), float(incoming.get("confidence") or 0.0))
        provenance = list(dict.fromkeys((merged.get("provenance") or []) + (incoming.get("provenance") or [])))
        merged["provenance"] = provenance
        return merged
