"""Standalone operations workflow service replacing Odoo-owned supplier workflow state."""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import RoutingDecisionResult, RoutingOutcome
from .operational_policy import queue_for_outcome
from .routing_service import RuleBasedBusinessFlowEngine, RoutingRules
from .sqlite_persistence import SqliteSupplierIntelligenceStore


@dataclass
class SupplierOperationsService:
    store: SqliteSupplierIntelligenceStore
    rules: RoutingRules | None = None

    def decide(
        self,
        company_key: str,
        reason_code: str = "",
        evidence_refs: list[str] | None = None,
        notes: str = "",
        manual_override: bool = False,
        forced_outcome: RoutingOutcome | None = None,
    ) -> RoutingDecisionResult:
        company = self.store.get_company_by_key(company_key)
        if not company:
            raise LookupError(f"company_key:{company_key}")

        profile = self.store.get_vendor_profile(company_key)
        score = self.store.get_score(company_key)
        if not score:
            raise ValueError(f"missing_score:{company_key}")

        has_pending_dedup, dedup_confidence = self.store.get_pending_dedup_signal(company_key)
        engine = RuleBasedBusinessFlowEngine(rules=self.rules or RoutingRules())
        outcome, inferred_reason = engine.decide(
            score=score,
            has_pending_dedup=has_pending_dedup,
            dedup_confidence=dedup_confidence,
            manual_override=forced_outcome if manual_override else None,
        )
        return self.store.apply_routing_decision(
            company_key=company_key,
            outcome=outcome,
            reason_code=reason_code or inferred_reason,
            evidence_refs=evidence_refs or [],
            notes=notes,
            manual_override=manual_override,
        )

    def queue_target_for_outcome(self, outcome: RoutingOutcome) -> str:
        return queue_for_outcome(outcome)
