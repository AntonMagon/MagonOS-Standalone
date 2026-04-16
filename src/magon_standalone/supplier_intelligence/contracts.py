"""Typed contracts shared by pipeline, routing, and workforce services.

Runtime role: Defines payload shapes used across runtime services and CLIs.
Inputs: Imports from services, tests, and scripts.
Outputs: TypedDicts and dataclasses.
Does not: perform validation against the database or store state.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Literal, TypedDict


SourceType = Literal["directory", "company_site", "maps_profile", "registry"]
ScenarioKey = Literal[
    "SIMPLE_DIRECTORY",
    "JS_DIRECTORY",
    "COMPANY_SITE",
    "HARD_DYNAMIC_OR_BLOCKED",
    "AI_ASSISTED_EXTRACTION",
]
PageType = Literal["directory", "company_site", "listing", "category", "article", "social", "pdf", "unknown"]
PaginationMode = Literal["none", "next_link", "numbered", "load_more", "infinite_scroll"]
ReviewStatus = Literal["new", "in_review", "approved", "rejected"]
DedupDecisionType = Literal["same_entity", "different_entity", "needs_manual_review"]
FetchStatus = Literal["ok", "partial", "failed"]
ExtractionMethod = Literal["deterministic", "heuristic", "ai_assisted"]
RoutingOutcome = Literal[
    "approved_supplier",
    "potential_supplier",
    "not_relevant",
    "duplicate",
    "unreachable",
    "needs_manual_review",
]
FeedbackEventType = Literal[
    "routing_feedback",
    "qualification_feedback",
    "partner_linkage_feedback",
    "commercial_disposition_feedback",
    "crm_lead_feedback",
]


class DiscoverySeed(TypedDict):
    query: str
    country_code: str
    source_type: SourceType
    source_url: str


class PageSeed(TypedDict, total=False):
    url: str
    query: str
    country_code: str
    source_type: SourceType
    source_domain: str
    page_type_hint: PageType
    discovered_at: str
    metadata: dict[str, Any]


class PageProfile(TypedDict, total=False):
    url: str
    source_domain: str
    page_type: PageType
    js_dependency: bool
    repeated_card_blocks: bool
    pagination_mode: PaginationMode
    structured_data_available: bool
    contact_density: float
    anti_bot_likelihood: float
    browser_required: bool
    xhr_candidate: bool
    profile_confidence: float
    signals: dict[str, Any]


class ScenarioRouteDecision(TypedDict, total=False):
    scenario_key: ScenarioKey
    reasons: list[str]
    execution_flags: dict[str, Any]
    escalation_policy: list[ScenarioKey]
    confidence: float


class RawEvidencePayload(TypedDict, total=False):
    evidence_ref: str
    source_url: str
    scenario_key: ScenarioKey
    evidence_type: Literal["html", "rendered_html", "card_block", "page_text", "screenshot", "event_log"]
    selector: str
    content: str
    metadata: dict[str, Any]


class RawCompanyRecord(TypedDict, total=False):
    source_type: SourceType
    source_url: str
    source_page_type: PageType
    source_domain: str
    external_id: str
    supplier_id: str
    company_name: str
    legal_name: str
    brand_alias: str
    supplier_type: str
    address_text: str
    region: str
    city: str
    district: str
    country: str
    phone: str
    phones: list[str]
    email: str
    emails: list[str]
    website: str
    domain: str
    categories: list[str]
    capabilities_text: str
    services: list[str]
    products: list[str]
    labels: list[str]
    contact_persons: list[str]
    messengers: list[str]
    social_links: list[str]
    min_order: str
    languages: list[str]
    fetched_at: str
    discovered_at: str
    extracted_at: str
    normalized_at: str
    fetch_status: FetchStatus
    parser_confidence: float
    source_confidence: float
    extraction_method: ExtractionMethod
    extraction_confidence: float
    scenario_key: ScenarioKey
    execution_reasons: list[str]
    execution_flags: dict[str, Any]
    raw_evidence_refs: list[str]
    evidence_payloads: list[RawEvidencePayload]
    escalation_count: int
    source_fingerprint: str
    candidate_dedup_fingerprint: str
    raw_payload: dict[str, Any]


class NormalizedCompanyRecord(TypedDict, total=False):
    canonical_key: str
    canonical_name: str
    legal_name: str
    brand_alias: str
    canonical_phone: str
    canonical_email: str
    website: str
    address_text: str
    city: str
    district: str
    country_code: str
    registration_code: str
    capabilities: list[str]
    confidence: float
    parser_confidence: float
    source_confidence: float
    provenance: list[str]
    review_status: ReviewStatus
    source_fingerprint: str
    dedup_fingerprint: str


class CompanyUpsertPayload(TypedDict, total=False):
    name: str
    legal_name: str
    brand_alias: str
    website: str
    phone: str
    email: str
    address_text: str
    city: str
    district: str
    country_code: str
    registration_code: str
    source_fingerprint: str
    dedup_fingerprint: str
    source_confidence: float
    quality_score: float
    manual_review_status: ReviewStatus
    source_count: int


class VendorProfileScorePayload(TypedDict):
    company_key: str
    relevance_score: float
    capability_fit_score: float
    contactability_score: float
    freshness_score: float
    trust_score: float
    composite_score: float
    parser_confidence: float


@dataclass(frozen=True)
class DedupDecisionPayload:
    left_company_key: str
    right_company_key: str
    decision: DedupDecisionType
    confidence: float
    pair_fingerprint: str
    match_signals: dict
    algorithm_version: str


@dataclass(frozen=True)
class SupplierScore:
    supplier_key: str
    quality_score: float
    readiness_score: float
    fit_score: float
    ranked_at: datetime


@dataclass(frozen=True)
class MatchRoutingInput:
    request_id: int
    specification_id: int
    supplier_key: str
    score: SupplierScore


@dataclass(frozen=True)
class QualificationDecisionInput:
    vendor_profile_id: int
    request_id: int | None
    decision: Literal["approve", "reject", "needs_info"]
    confidence: float
    rationale: str
    algorithm_version: str


class ReviewQueueItem(TypedDict):
    company_key: str
    queue_name: Literal["supplier_review", "dedup_review", "qualification_review"]
    priority: int
    reason: str
    score: float


class FeedbackStatusProjection(TypedDict, total=False):
    source_key: str
    company_id: int | None
    vendor_profile_id: int | None
    last_event_id: str | None
    last_event_type: str | None
    last_event_at: str | None
    last_event_is_synthetic: bool
    routing_event_id: str | None
    routing_outcome: str | None
    manual_review_status: str | None
    routing_reason_code: str | None
    routing_notes: str | None
    routing_is_manual_override: bool
    routing_is_synthetic: bool
    routing_occurred_at: str | None
    qualification_event_id: str | None
    qualification_decision_id: int | None
    qualification_status: str | None
    qualification_reason_code: str | None
    qualification_notes: str | None
    qualification_is_manual_override: bool
    qualification_is_synthetic: bool
    qualification_occurred_at: str | None
    partner_linkage_event_id: str | None
    partner_id: int | None
    partner_linked: bool
    partner_is_synthetic: bool
    partner_occurred_at: str | None
    commercial_event_id: str | None
    crm_lead_id: int | None
    lead_mapping_id: int | None
    lead_status: str | None
    crm_linked: bool
    commercial_reason_code: str | None
    commercial_notes: str | None
    commercial_is_manual_override: bool
    commercial_is_synthetic: bool
    commercial_occurred_at: str | None
    updated_at: str | None


class RoutingDecisionInput(TypedDict, total=False):
    company_key: str
    reason_code: str
    evidence_refs: list[str]
    notes: str
    manual_override: bool


@dataclass(frozen=True)
class RoutingDecisionResult:
    company_key: str
    outcome: RoutingOutcome
    reason_code: str
    queue_name: str
    score: float
    outreach_ready: bool
    rfq_ready: bool


@dataclass(frozen=True)
class FeedbackEventPayload:
    event_id: str
    source_key: str
    source_system: Literal["odoo"]
    event_type: FeedbackEventType
    event_version: str
    occurred_at: str
    payload_hash: str
    company_id: int | None = None
    vendor_profile_id: int | None = None
    qualification_decision_id: int | None = None
    partner_id: int | None = None
    crm_lead_id: int | None = None
    lead_mapping_id: int | None = None
    routing_outcome: str | None = None
    manual_review_status: str | None = None
    qualification_status: str | None = None
    lead_status: str | None = None
    partner_linked: bool = False
    crm_linked: bool = False
    reason_code: str | None = None
    notes: str | None = None
    is_manual_override: bool = False
    is_synthetic: bool = False
    payload: dict[str, Any] | None = None


DEPRECATED_FEEDBACK_EVENT_TYPE_ALIASES: dict[str, str] = {
    "crm_lead_feedback": "commercial_disposition_feedback",
}

ALLOWED_FEEDBACK_EVENT_TYPES: tuple[str, ...] = (
    "routing_feedback",
    "qualification_feedback",
    "partner_linkage_feedback",
    "commercial_disposition_feedback",
)

FORBIDDEN_FEEDBACK_KEYS: frozenset[str] = frozenset(
    {
        "raw_payload",
        "raw_discovery_payload",
        "raw_evidence",
        "canonical_name",
        "company_name",
        "legal_name",
        "brand_alias",
        "website",
        "domain",
        "email",
        "emails",
        "phone",
        "phones",
        "address",
        "address_text",
        "city",
        "district",
        "region",
        "country",
        "country_code",
        "categories",
        "services",
        "products",
        "labels",
        "contact_persons",
        "messengers",
        "social_links",
        "languages",
        "normalization_output",
        "normalized_record",
        "score",
        "scores",
        "quality_score",
        "trust_score",
        "parser_confidence",
        "dedup_decision",
        "dedup_decisions",
        "match_signals",
        "partner_name",
        "partner_email",
        "partner_phone",
        "partner_address",
        "crm_stage",
        "crm_stage_id",
        "crm_stage_history",
        "crm_owner_id",
        "crm_activity",
        "crm_activity_ids",
        "quote_id",
        "quote_amount",
        "order_id",
        "purchase_order_id",
        "invoice_id",
        "payment_id",
        "margin",
        "price",
        "pricing",
    }
)

_BASE_FEEDBACK_FIELDS = frozenset(
    {
        "event_id",
        "source_key",
        "source_system",
        "event_type",
        "event_version",
        "occurred_at",
        "payload_hash",
        "payload",
        "is_synthetic",
    }
)

ALLOWED_EVENT_TOP_LEVEL_FIELDS: dict[str, frozenset[str]] = {
    "routing_feedback": _BASE_FEEDBACK_FIELDS
    | frozenset(
        {
            "company_id",
            "vendor_profile_id",
            "routing_outcome",
            "manual_review_status",
            "reason_code",
            "notes",
            "is_manual_override",
        }
    ),
    "qualification_feedback": _BASE_FEEDBACK_FIELDS
    | frozenset(
        {
            "company_id",
            "vendor_profile_id",
            "qualification_decision_id",
            "qualification_status",
            "reason_code",
            "notes",
            "is_manual_override",
        }
    ),
    "partner_linkage_feedback": _BASE_FEEDBACK_FIELDS
    | frozenset(
        {
            "company_id",
            "vendor_profile_id",
            "partner_id",
            "partner_linked",
        }
    ),
    "commercial_disposition_feedback": _BASE_FEEDBACK_FIELDS
    | frozenset(
        {
            "company_id",
            "vendor_profile_id",
            "crm_lead_id",
            "lead_mapping_id",
            "lead_status",
            "crm_linked",
            "reason_code",
            "notes",
            "is_manual_override",
        }
    ),
}

ALLOWED_EVENT_PAYLOAD_FIELDS: dict[str, frozenset[str]] = {
    "routing_feedback": frozenset(
        {
            "routing_outcome",
            "manual_review_status",
            "reason_code",
            "notes",
            "is_manual_override",
        }
    ),
    "qualification_feedback": frozenset(
        {
            "qualification_decision_id",
            "qualification_status",
            "reason_code",
            "notes",
            "is_manual_override",
        }
    ),
    "partner_linkage_feedback": frozenset(
        {
            "partner_id",
            "partner_linked",
        }
    ),
    "commercial_disposition_feedback": frozenset(
        {
            "crm_lead_id",
            "lead_mapping_id",
            "lead_status",
            "crm_linked",
            "reason_code",
            "notes",
            "is_manual_override",
        }
    ),
}

EVENT_FIELD_TO_ATTRIBUTE: dict[str, tuple[str, ...]] = {
    "routing_feedback": ("routing_outcome", "manual_review_status", "reason_code", "notes", "is_manual_override"),
    "qualification_feedback": ("qualification_decision_id", "qualification_status", "reason_code", "notes", "is_manual_override"),
    "partner_linkage_feedback": ("partner_id", "partner_linked"),
    "commercial_disposition_feedback": ("crm_lead_id", "lead_mapping_id", "lead_status", "crm_linked", "reason_code", "notes", "is_manual_override"),
}


def normalize_feedback_event_type(event_type: str) -> str:
    normalized = DEPRECATED_FEEDBACK_EVENT_TYPE_ALIASES.get(event_type, event_type)
    if normalized not in ALLOWED_FEEDBACK_EVENT_TYPES:
        raise ValueError(f"unsupported_feedback_event_type:{event_type}")
    return normalized


def validate_feedback_event(event: FeedbackEventPayload) -> FeedbackEventPayload:
    event_type = normalize_feedback_event_type(event.event_type)
    payload = dict(event.payload or {})
    _reject_forbidden_feedback_keys(payload.keys())

    if event.source_system != "odoo":
        raise ValueError("unsupported_feedback_source_system")
    if not event.event_id:
        raise ValueError("feedback_event_id_required")
    if not event.source_key:
        raise ValueError("feedback_source_key_required")
    if not event.event_version:
        raise ValueError("feedback_event_version_required")
    if not event.occurred_at:
        raise ValueError("feedback_occurred_at_required")
    if not event.payload_hash:
        raise ValueError("feedback_payload_hash_required")

    allowed_payload_fields = ALLOWED_EVENT_PAYLOAD_FIELDS[event_type]
    unknown_payload_fields = set(payload) - set(allowed_payload_fields)
    if unknown_payload_fields:
        bad = ",".join(sorted(unknown_payload_fields))
        raise ValueError(f"feedback_payload_fields_forbidden:{event_type}:{bad}")

    allowed_top_level_fields = ALLOWED_EVENT_TOP_LEVEL_FIELDS[event_type]
    event_dict = event.__dict__
    for key, value in event_dict.items():
        if key in _BASE_FEEDBACK_FIELDS or key in allowed_top_level_fields:
            continue
        if _has_meaningful_value(value):
            raise ValueError(f"feedback_top_level_field_forbidden:{event_type}:{key}")

    merged_payload = dict(payload)
    for field_name in EVENT_FIELD_TO_ATTRIBUTE[event_type]:
        attr_value = event_dict.get(field_name)
        if not _has_meaningful_value(attr_value):
            continue
        if field_name in merged_payload and merged_payload[field_name] != attr_value:
            raise ValueError(f"feedback_payload_mismatch:{event_type}:{field_name}")
        merged_payload[field_name] = attr_value

    if event_type == "routing_feedback" and not (
        _has_meaningful_value(event.routing_outcome) or _has_meaningful_value(event.manual_review_status)
    ):
        raise ValueError("routing_feedback_requires_outcome_or_review_status")
    if event_type == "qualification_feedback" and not (
        _has_meaningful_value(event.qualification_status) or _has_meaningful_value(event.qualification_decision_id)
    ):
        raise ValueError("qualification_feedback_requires_status_or_decision")
    if event_type == "partner_linkage_feedback" and not _has_meaningful_value(event.partner_id):
        raise ValueError("partner_linkage_feedback_requires_partner_id")
    if event_type == "commercial_disposition_feedback" and not (
        _has_meaningful_value(event.crm_lead_id)
        or _has_meaningful_value(event.lead_mapping_id)
        or _has_meaningful_value(event.lead_status)
    ):
        raise ValueError("commercial_disposition_feedback_requires_commercial_reference")

    return replace(event, event_type=event_type, payload=merged_payload)


def _reject_forbidden_feedback_keys(keys: set[str] | list[str] | tuple[str, ...]) -> None:
    bad = sorted(set(keys) & FORBIDDEN_FEEDBACK_KEYS)
    if bad:
        raise ValueError(f"feedback_payload_contains_forbidden_fields:{','.join(bad)}")


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if value is False:
        return False
    if value == "":
        return False
    if isinstance(value, (list, dict, tuple, set)) and not value:
        return False
    return True


@dataclass(frozen=True)
class WorkforceEstimateInput:
    specification_id: int | None
    process_type: str
    quantity: float
    complexity_level: str
    target_completion_hours: float | None
    role_demands: list["WorkforceRoleDemand"]
    shift_capacities: list["ShiftCapacityInput"]
    labor_rates: list["LaborRateInput"]
    policies: list["LaborPolicyInput"]


@dataclass(frozen=True)
class WorkforceEstimateResult:
    specification_id: int | None
    estimated_hours: float
    required_headcount: int
    standard_labor_cost: float
    overtime_cost: float
    total_labor_cost: float
    overtime_required: bool
    time_remaining_hours: float
    bottleneck_role_code: str | None
    missing_skill_roles: list[str]
    role_breakdown: list["RoleEstimateBreakdown"]
    assumptions: list[str]


@dataclass(frozen=True)
class WorkforceRoleDemand:
    role_code: str
    required_skill_codes: list[str]
    hours_per_unit: float
    quantity_factor: float = 1.0


@dataclass(frozen=True)
class ShiftCapacityInput:
    role_code: str
    shift_hours: float
    worker_count: int
    absence_count: int = 0
    available_skill_codes: list[str] | None = None
    slot_available_hours: float | None = None


@dataclass(frozen=True)
class LaborRateInput:
    role_code: str
    base_hourly_rate: float
    overtime_multiplier: float = 1.5
    overtime_threshold_hours: float = 8.0
    currency_code: str = "VND"


@dataclass(frozen=True)
class LaborPolicyInput:
    code: str
    country_code: str = "VN"
    value_float: float | None = None
    value_int: int | None = None
    value_text: str | None = None


@dataclass(frozen=True)
class RoleEstimateBreakdown:
    role_code: str
    required_hours: float
    available_hours: float
    estimated_headcount: int
    standard_hours: float
    overtime_hours: float
    standard_cost: float
    overtime_cost: float
    bottleneck: bool
