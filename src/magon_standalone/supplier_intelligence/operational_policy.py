"""Standalone workflow policy helpers for supplier operations state."""
from __future__ import annotations

from .contracts import RoutingOutcome


def default_vendor_profile_state(composite_score: float) -> dict[str, object]:
    return {
        "review_status": "new",
        "qualification_status": "provisional" if composite_score >= 0.55 else "unqualified",
        "outreach_ready": False,
        "rfq_ready": False,
        "lifecycle_state": "new",
        "routing_state": "unreviewed",
    }


def merge_vendor_profile_state(
    existing_state: dict[str, object] | None,
    routing_state: str | None,
    composite_score: float,
) -> dict[str, object]:
    defaults = default_vendor_profile_state(composite_score)
    if not existing_state:
        return defaults
    if routing_state and routing_state != "unreviewed":
        return {
            "review_status": existing_state.get("review_status") or defaults["review_status"],
            "qualification_status": existing_state.get("qualification_status") or defaults["qualification_status"],
            "outreach_ready": bool(existing_state.get("outreach_ready")),
            "rfq_ready": bool(existing_state.get("rfq_ready")),
            "lifecycle_state": existing_state.get("lifecycle_state") or defaults["lifecycle_state"],
            "routing_state": existing_state.get("routing_state") or routing_state,
        }
    return defaults


def pipeline_queue_status(routing_state: str | None) -> str:
    if routing_state in {None, "", "unreviewed", "needs_manual_review"}:
        return "pending"
    return "done"


def queue_for_outcome(outcome: RoutingOutcome) -> str:
    if outcome in {"approved_supplier", "potential_supplier"}:
        return "qualification_review"
    if outcome == "duplicate":
        return "dedup_review"
    return "supplier_review"


def outcome_profile_state(outcome: RoutingOutcome) -> tuple[str, str, str]:
    status_map = {
        "approved_supplier": ("approved", "qualified", "active"),
        "potential_supplier": ("in_review", "provisional", "active"),
        "not_relevant": ("rejected", "blocked", "rejected"),
        "duplicate": ("rejected", "blocked", "rejected"),
        "unreachable": ("rejected", "unqualified", "quarantine"),
        "needs_manual_review": ("in_review", "unqualified", "quarantine"),
    }
    return status_map[outcome]
