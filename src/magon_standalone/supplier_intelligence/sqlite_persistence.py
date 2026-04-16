"""SQLite persistence adapter for the standalone supplier-intelligence slice.

Runtime role: Implements the standalone persistence ports with one local SQLite
database that can be run without Odoo.
Inputs: Typed raw/canonical/score/dedup/queue payloads from platform_core.
Outputs: Durable standalone records for the extracted supplier-intelligence domain.
Does not: perform CRM/commercial side effects or import Odoo.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import (
    DedupDecisionPayload,
    FeedbackEventPayload,
    FeedbackStatusProjection,
    NormalizedCompanyRecord,
    RawCompanyRecord,
    ReviewQueueItem,
    RoutingDecisionResult,
    RoutingOutcome,
    VendorProfileScorePayload,
    validate_feedback_event,
)
from .operational_policy import merge_vendor_profile_state, outcome_profile_state, pipeline_queue_status, queue_for_outcome
from .interfaces import SupplierIntelligencePersistence


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False, sort_keys=True)


def _optional_db_int(value: Any) -> int | None:
    if value in {None, "", False}:
        return None
    return int(value)


class SqliteSupplierIntelligenceStore(SupplierIntelligencePersistence):
    """Persist the extracted supplier-intelligence slice into a local SQLite file."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS raw_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_fingerprint TEXT UNIQUE NOT NULL,
                    candidate_dedup_fingerprint TEXT,
                    source_type TEXT,
                    source_url TEXT,
                    source_page_type TEXT,
                    source_domain TEXT,
                    external_id TEXT,
                    supplier_id TEXT,
                    company_name TEXT,
                    legal_name TEXT,
                    brand_alias TEXT,
                    supplier_type TEXT,
                    address_text TEXT,
                    region TEXT,
                    city TEXT,
                    district TEXT,
                    country TEXT,
                    phone TEXT,
                    email TEXT,
                    website TEXT,
                    domain TEXT,
                    min_order TEXT,
                    capabilities_text TEXT,
                    fetch_status TEXT,
                    parser_confidence REAL,
                    source_confidence REAL,
                    extraction_method TEXT,
                    extraction_confidence REAL,
                    scenario_key TEXT,
                    escalation_count INTEGER,
                    fetched_at TEXT,
                    discovered_at TEXT,
                    extracted_at TEXT,
                    normalized_at TEXT,
                    categories_json TEXT,
                    services_json TEXT,
                    products_json TEXT,
                    labels_json TEXT,
                    phones_json TEXT,
                    emails_json TEXT,
                    contact_persons_json TEXT,
                    messengers_json TEXT,
                    social_links_json TEXT,
                    languages_json TEXT,
                    execution_reasons_json TEXT,
                    execution_flags_json TEXT,
                    raw_payload_json TEXT,
                    raw_evidence_refs_json TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS raw_evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_record_id INTEGER NOT NULL,
                    evidence_ref TEXT,
                    source_url TEXT,
                    scenario_key TEXT,
                    evidence_type TEXT,
                    selector TEXT,
                    content TEXT,
                    metadata_json TEXT,
                    UNIQUE(raw_record_id, evidence_ref, source_url, evidence_type),
                    FOREIGN KEY(raw_record_id) REFERENCES raw_records(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS canonical_companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_key TEXT UNIQUE NOT NULL,
                    canonical_name TEXT,
                    legal_name TEXT,
                    brand_alias TEXT,
                    canonical_phone TEXT,
                    canonical_email TEXT,
                    website TEXT,
                    address_text TEXT,
                    city TEXT,
                    district TEXT,
                    country_code TEXT,
                    registration_code TEXT,
                    capabilities_json TEXT,
                    confidence REAL,
                    parser_confidence REAL,
                    source_confidence REAL,
                    normalized_at TEXT,
                    provenance_json TEXT,
                    review_status TEXT,
                    source_fingerprint TEXT,
                    dedup_fingerprint TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS vendor_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT UNIQUE NOT NULL,
                    relevance_score REAL,
                    capability_fit_score REAL,
                    contactability_score REAL,
                    freshness_score REAL,
                    trust_score REAL,
                    composite_score REAL,
                    parser_confidence REAL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS dedup_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair_fingerprint TEXT UNIQUE NOT NULL,
                    left_company_key TEXT,
                    right_company_key TEXT,
                    decision TEXT,
                    confidence REAL,
                    match_signals_json TEXT,
                    algorithm_version TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    queue_name TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    reason TEXT,
                    reason_code TEXT,
                    evidence_refs_json TEXT,
                    score REAL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    reprocess_count INTEGER NOT NULL DEFAULT 0,
                    last_transition_at TEXT,
                    updated_at TEXT NOT NULL,
                    UNIQUE(company_key, queue_name)
                );

                CREATE TABLE IF NOT EXISTS vendor_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT UNIQUE NOT NULL,
                    review_status TEXT NOT NULL,
                    qualification_status TEXT NOT NULL,
                    relevance_score REAL NOT NULL DEFAULT 0,
                    capability_fit_score REAL NOT NULL DEFAULT 0,
                    contactability_score REAL NOT NULL DEFAULT 0,
                    freshness_score REAL NOT NULL DEFAULT 0,
                    trust_score REAL NOT NULL DEFAULT 0,
                    composite_score REAL NOT NULL DEFAULT 0,
                    parser_confidence REAL NOT NULL DEFAULT 0,
                    outreach_ready INTEGER NOT NULL DEFAULT 0,
                    rfq_ready INTEGER NOT NULL DEFAULT 0,
                    lifecycle_state TEXT NOT NULL DEFAULT 'new',
                    routing_state TEXT NOT NULL DEFAULT 'unreviewed',
                    notes TEXT,
                    last_routed_at TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS qualification_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    vendor_profile_id INTEGER,
                    decision TEXT NOT NULL,
                    route_outcome TEXT NOT NULL,
                    reason_code TEXT,
                    evidence_refs_json TEXT,
                    internal_note TEXT,
                    reprocess_token TEXT,
                    decision_confidence REAL NOT NULL DEFAULT 0,
                    rationale TEXT,
                    algorithm_version TEXT,
                    decision_at TEXT NOT NULL,
                    decided_by TEXT,
                    is_manual_override INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE,
                    FOREIGN KEY(vendor_profile_id) REFERENCES vendor_profiles(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS routing_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    queue_name TEXT,
                    vendor_profile_id INTEGER,
                    qualification_decision_id INTEGER,
                    event_type TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT,
                    reason_code TEXT,
                    evidence_refs_json TEXT,
                    notes TEXT,
                    is_manual_override INTEGER NOT NULL DEFAULT 0,
                    actor TEXT,
                    event_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE,
                    FOREIGN KEY(vendor_profile_id) REFERENCES vendor_profiles(id) ON DELETE SET NULL,
                    FOREIGN KEY(qualification_decision_id) REFERENCES qualification_decisions(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS commercial_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT UNIQUE NOT NULL,
                    customer_status TEXT NOT NULL DEFAULT 'prospect',
                    commercial_stage TEXT NOT NULL DEFAULT 'new_lead',
                    customer_reference TEXT,
                    opportunity_reference TEXT,
                    next_action TEXT,
                    next_action_due_at TEXT,
                    notes TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS customer_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT UNIQUE NOT NULL,
                    account_name TEXT NOT NULL,
                    account_type TEXT NOT NULL DEFAULT 'direct_customer',
                    account_status TEXT NOT NULL DEFAULT 'prospect',
                    primary_contact_name TEXT,
                    primary_email TEXT,
                    primary_phone TEXT,
                    billing_city TEXT,
                    external_customer_ref TEXT,
                    odoo_partner_ref TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS commercial_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    customer_account_id INTEGER,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    source_channel TEXT,
                    estimated_value REAL,
                    currency_code TEXT NOT NULL DEFAULT 'VND',
                    target_due_at TEXT,
                    next_action TEXT,
                    notes TEXT,
                    external_opportunity_ref TEXT,
                    odoo_lead_ref TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE,
                    FOREIGN KEY(customer_account_id) REFERENCES customer_accounts(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS quote_intents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    customer_account_id INTEGER,
                    opportunity_id INTEGER,
                    quote_type TEXT NOT NULL,
                    quantity_hint TEXT,
                    target_due_at TEXT,
                    status TEXT NOT NULL DEFAULT 'requested',
                    rfq_reference TEXT,
                    quote_reference TEXT,
                    quoted_amount REAL,
                    currency_code TEXT NOT NULL DEFAULT 'VND',
                    pricing_notes TEXT,
                    last_status_at TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE,
                    FOREIGN KEY(customer_account_id) REFERENCES customer_accounts(id) ON DELETE SET NULL,
                    FOREIGN KEY(opportunity_id) REFERENCES commercial_opportunities(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS production_handoffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    quote_intent_id INTEGER,
                    handoff_status TEXT NOT NULL DEFAULT 'ready_for_production',
                    production_reference TEXT,
                    requested_ship_at TEXT,
                    specification_summary TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE,
                    FOREIGN KEY(quote_intent_id) REFERENCES quote_intents(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS feedback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    source_key TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_version TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    company_id INTEGER,
                    vendor_profile_id INTEGER,
                    qualification_decision_id INTEGER,
                    partner_id INTEGER,
                    crm_lead_id INTEGER,
                    lead_mapping_id INTEGER,
                    routing_outcome TEXT,
                    manual_review_status TEXT,
                    qualification_status TEXT,
                    lead_status TEXT,
                    partner_linked INTEGER NOT NULL DEFAULT 0,
                    crm_linked INTEGER NOT NULL DEFAULT 0,
                    reason_code TEXT,
                    notes TEXT,
                    is_manual_override INTEGER NOT NULL DEFAULT 0,
                    is_synthetic INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT,
                    applied_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS feedback_status_projection (
                    source_key TEXT PRIMARY KEY,
                    company_id INTEGER,
                    vendor_profile_id INTEGER,
                    last_event_id TEXT,
                    last_event_type TEXT,
                    last_event_at TEXT,
                    last_event_is_synthetic INTEGER NOT NULL DEFAULT 0,
                    routing_event_id TEXT,
                    routing_outcome TEXT,
                    manual_review_status TEXT,
                    routing_reason_code TEXT,
                    routing_notes TEXT,
                    routing_is_manual_override INTEGER NOT NULL DEFAULT 0,
                    routing_is_synthetic INTEGER NOT NULL DEFAULT 0,
                    routing_occurred_at TEXT,
                    qualification_event_id TEXT,
                    qualification_decision_id INTEGER,
                    qualification_status TEXT,
                    qualification_reason_code TEXT,
                    qualification_notes TEXT,
                    qualification_is_manual_override INTEGER NOT NULL DEFAULT 0,
                    qualification_is_synthetic INTEGER NOT NULL DEFAULT 0,
                    qualification_occurred_at TEXT,
                    partner_linkage_event_id TEXT,
                    partner_id INTEGER,
                    partner_linked INTEGER NOT NULL DEFAULT 0,
                    partner_is_synthetic INTEGER NOT NULL DEFAULT 0,
                    partner_occurred_at TEXT,
                    commercial_event_id TEXT,
                    crm_lead_id INTEGER,
                    lead_mapping_id INTEGER,
                    lead_status TEXT,
                    crm_linked INTEGER NOT NULL DEFAULT 0,
                    commercial_reason_code TEXT,
                    commercial_notes TEXT,
                    commercial_is_manual_override INTEGER NOT NULL DEFAULT 0,
                    commercial_is_synthetic INTEGER NOT NULL DEFAULT 0,
                    commercial_occurred_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS commercial_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_key TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    previous_status TEXT,
                    new_status TEXT,
                    note TEXT,
                    actor TEXT,
                    metadata_json TEXT,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY(company_key) REFERENCES canonical_companies(canonical_key) ON DELETE CASCADE
                );
                """
            )
            self._ensure_columns(conn, "feedback_events", {"is_synthetic": "INTEGER NOT NULL DEFAULT 0"})
            self._ensure_columns(
                conn,
                "review_queue",
                {
                    "reason_code": "TEXT",
                    "evidence_refs_json": "TEXT",
                    "reprocess_count": "INTEGER NOT NULL DEFAULT 0",
                    "last_transition_at": "TEXT",
                },
            )
            self._ensure_columns(
                conn,
                "feedback_status_projection",
                {
                    "last_event_is_synthetic": "INTEGER NOT NULL DEFAULT 0",
                    "routing_is_synthetic": "INTEGER NOT NULL DEFAULT 0",
                    "qualification_is_synthetic": "INTEGER NOT NULL DEFAULT 0",
                    "partner_is_synthetic": "INTEGER NOT NULL DEFAULT 0",
                    "commercial_is_synthetic": "INTEGER NOT NULL DEFAULT 0",
                },
            )
            self._ensure_columns(
                conn,
                "vendor_profiles",
                {
                    "routing_state": "TEXT NOT NULL DEFAULT 'unreviewed'",
                    "last_routed_at": "TEXT",
                },
            )
            self._ensure_columns(
                conn,
                "quote_intents",
                {
                    "customer_account_id": "INTEGER",
                    "opportunity_id": "INTEGER",
                    "rfq_reference": "TEXT",
                    "quote_reference": "TEXT",
                    "quoted_amount": "REAL",
                    "currency_code": "TEXT NOT NULL DEFAULT 'VND'",
                    "pricing_notes": "TEXT",
                    "last_status_at": "TEXT",
                },
            )
            self._ensure_columns(
                conn,
                "production_handoffs",
                {},
            )

    @staticmethod
    def _ensure_columns(conn: sqlite3.Connection, table: str, specs: dict[str, str]) -> None:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for column_name, ddl in specs.items():
            if column_name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {ddl}")

    def save_raw_records(self, records: list[RawCompanyRecord]) -> list[int]:
        ids: list[int] = []
        with self._connect() as conn:
            for item in records:
                payload = self._raw_row(item)
                columns = ", ".join(payload.keys())
                placeholders = ", ".join(f":{key}" for key in payload.keys())
                updates = ", ".join(f"{key}=excluded.{key}" for key in payload.keys() if key != "source_fingerprint")
                conn.execute(
                    f"""
                    INSERT INTO raw_records ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT(source_fingerprint) DO UPDATE SET {updates}
                    """,
                    payload,
                )
                row_id = conn.execute(
                    "SELECT id FROM raw_records WHERE source_fingerprint = ?",
                    (item.get("source_fingerprint") or "",),
                ).fetchone()["id"]
                self._upsert_evidence(conn, row_id, item)
                ids.append(int(row_id))
        return ids

    def upsert_companies(self, records: list[NormalizedCompanyRecord]) -> dict[str, int]:
        company_ids: dict[str, int] = {}
        with self._connect() as conn:
            for item in records:
                payload = self._company_row(item)
                columns = ", ".join(payload.keys())
                placeholders = ", ".join(f":{key}" for key in payload.keys())
                updates = ", ".join(f"{key}=excluded.{key}" for key in payload.keys() if key != "canonical_key")
                conn.execute(
                    f"""
                    INSERT INTO canonical_companies ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT(canonical_key) DO UPDATE SET {updates}
                    """,
                    payload,
                )
                row_id = conn.execute(
                    "SELECT id FROM canonical_companies WHERE canonical_key = ?",
                    (item["canonical_key"],),
                ).fetchone()["id"]
                company_ids[item["canonical_key"]] = int(row_id)
        return company_ids

    def save_vendor_scores(self, scores: list[VendorProfileScorePayload], company_ids: dict[str, int]) -> None:
        with self._connect() as conn:
            for item in scores:
                payload = {
                    **item,
                    "updated_at": _utc_now(),
                }
                columns = ", ".join(payload.keys())
                placeholders = ", ".join(f":{key}" for key in payload.keys())
                updates = ", ".join(f"{key}=excluded.{key}" for key in payload.keys() if key != "company_key")
                conn.execute(
                    f"""
                    INSERT INTO vendor_scores ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT(company_key) DO UPDATE SET {updates}
                    """,
                    payload,
                )
                existing_profile = conn.execute(
                    "SELECT * FROM vendor_profiles WHERE company_key = ?",
                    (item["company_key"],),
                ).fetchone()
                workflow_state = merge_vendor_profile_state(
                    existing_state=dict(existing_profile) if existing_profile else None,
                    routing_state=(existing_profile["routing_state"] if existing_profile else None),
                    composite_score=float(item.get("composite_score") or 0.0),
                )
                profile_payload = {
                    "company_key": item["company_key"],
                    "review_status": str(workflow_state["review_status"]),
                    "qualification_status": str(workflow_state["qualification_status"]),
                    "relevance_score": float(item.get("relevance_score") or 0.0),
                    "capability_fit_score": float(item.get("capability_fit_score") or 0.0),
                    "contactability_score": float(item.get("contactability_score") or 0.0),
                    "freshness_score": float(item.get("freshness_score") or 0.0),
                    "trust_score": float(item.get("trust_score") or 0.0),
                    "composite_score": float(item.get("composite_score") or 0.0),
                    "parser_confidence": float(item.get("parser_confidence") or 0.0),
                    "outreach_ready": 1 if workflow_state["outreach_ready"] else 0,
                    "rfq_ready": 1 if workflow_state["rfq_ready"] else 0,
                    "lifecycle_state": str(workflow_state["lifecycle_state"]),
                    "routing_state": str(workflow_state["routing_state"]),
                    "notes": existing_profile["notes"] if existing_profile else "",
                    "last_routed_at": existing_profile["last_routed_at"] if existing_profile else None,
                    "updated_at": _utc_now(),
                }
                columns = ", ".join(profile_payload.keys())
                placeholders = ", ".join(f":{key}" for key in profile_payload.keys())
                updates = ", ".join(f"{key}=excluded.{key}" for key in profile_payload.keys() if key != "company_key")
                conn.execute(
                    f"""
                    INSERT INTO vendor_profiles ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT(company_key) DO UPDATE SET {updates}
                    """,
                    profile_payload,
                )

    def save_dedup_decisions(self, decisions: list[DedupDecisionPayload], company_ids: dict[str, int]) -> None:
        with self._connect() as conn:
            for item in decisions:
                payload = {
                    "pair_fingerprint": item.pair_fingerprint,
                    "left_company_key": item.left_company_key,
                    "right_company_key": item.right_company_key,
                    "decision": item.decision,
                    "confidence": item.confidence,
                    "match_signals_json": _json(item.match_signals),
                    "algorithm_version": item.algorithm_version,
                    "updated_at": _utc_now(),
                }
                columns = ", ".join(payload.keys())
                placeholders = ", ".join(f":{key}" for key in payload.keys())
                updates = ", ".join(f"{key}=excluded.{key}" for key in payload.keys() if key != "pair_fingerprint")
                conn.execute(
                    f"""
                    INSERT INTO dedup_decisions ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT(pair_fingerprint) DO UPDATE SET {updates}
                    """,
                    payload,
                )

    def route_review_queue(self, items: list[ReviewQueueItem], company_ids: dict[str, int]) -> int:
        created_or_updated = 0
        with self._connect() as conn:
            for item in items:
                profile = conn.execute(
                    "SELECT routing_state FROM vendor_profiles WHERE company_key = ?",
                    (item["company_key"],),
                ).fetchone()
                existing_queue = conn.execute(
                    """
                    SELECT *
                    FROM review_queue
                    WHERE company_key = ? AND queue_name = ?
                    LIMIT 1
                    """,
                    (item["company_key"], item["queue_name"]),
                ).fetchone()
                desired_status = pipeline_queue_status(profile["routing_state"] if profile else None)
                effective_status = desired_status
                preserve_operator_state = False
                if existing_queue is not None and desired_status == "pending" and existing_queue["status"] in {"in_progress", "done", "dismissed"}:
                    effective_status = existing_queue["status"]
                    preserve_operator_state = True
                payload = {
                    "company_key": item["company_key"],
                    "queue_name": item["queue_name"],
                    "priority": item["priority"],
                    "reason": existing_queue["reason"] if preserve_operator_state else item["reason"],
                    "reason_code": existing_queue["reason_code"] if preserve_operator_state else "auto_pipeline",
                    "evidence_refs_json": existing_queue["evidence_refs_json"] if preserve_operator_state else _json([]),
                    "score": item["score"],
                    "status": effective_status,
                    "reprocess_count": int(existing_queue["reprocess_count"] or 0) if existing_queue else 0,
                    "last_transition_at": existing_queue["last_transition_at"] if preserve_operator_state else _utc_now(),
                    "updated_at": _utc_now(),
                }
                columns = ", ".join(payload.keys())
                placeholders = ", ".join(f":{key}" for key in payload.keys())
                updates = ", ".join(
                    f"{key}=excluded.{key}"
                    for key in payload.keys()
                    if key not in {"company_key", "queue_name"}
                )
                conn.execute(
                    f"""
                    INSERT INTO review_queue ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT(company_key, queue_name) DO UPDATE SET {updates}
                    """,
                    payload,
                )
                created_or_updated += 1
        return created_or_updated

    def save_feedback_events(self, events: list[FeedbackEventPayload]) -> int:
        applied = 0
        with self._connect() as conn:
            for event in events:
                event = validate_feedback_event(event)
                payload = {
                    "event_id": event.event_id,
                    "source_key": event.source_key,
                    "source_system": event.source_system,
                    "event_type": event.event_type,
                    "event_version": event.event_version,
                    "occurred_at": event.occurred_at,
                    "payload_hash": event.payload_hash,
                    "company_id": event.company_id,
                    "vendor_profile_id": event.vendor_profile_id,
                    "qualification_decision_id": event.qualification_decision_id,
                    "partner_id": event.partner_id,
                    "crm_lead_id": event.crm_lead_id,
                    "lead_mapping_id": event.lead_mapping_id,
                    "routing_outcome": event.routing_outcome or "",
                    "manual_review_status": event.manual_review_status or "",
                    "qualification_status": event.qualification_status or "",
                    "lead_status": event.lead_status or "",
                    "partner_linked": 1 if event.partner_linked else 0,
                    "crm_linked": 1 if event.crm_linked else 0,
                    "reason_code": event.reason_code or "",
                    "notes": event.notes or "",
                    "is_manual_override": 1 if event.is_manual_override else 0,
                    "is_synthetic": 1 if event.is_synthetic else 0,
                    "payload_json": _json(event.payload or {}),
                    "applied_at": _utc_now(),
                    "updated_at": _utc_now(),
                }
                columns = ", ".join(payload.keys())
                placeholders = ", ".join(f":{key}" for key in payload.keys())
                updates = ", ".join(f"{key}=excluded.{key}" for key in payload.keys() if key != "event_id")
                before = conn.execute(
                    "SELECT payload_hash FROM feedback_events WHERE event_id = ?",
                    (event.event_id,),
                ).fetchone()
                conn.execute(
                    f"""
                    INSERT INTO feedback_events ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT(event_id) DO UPDATE SET {updates}
                    """,
                    payload,
                )
                after = payload["payload_hash"]
                if before is None or before["payload_hash"] != after:
                    self._apply_feedback_projection(conn, event)
                    applied += 1
        return applied

    def snapshot_counts(self) -> dict[str, int]:
        """Return one compact count summary for verification and CLI reporting."""
        with self._connect() as conn:
            return {
                "raw_records": self._count(conn, "raw_records"),
                "raw_evidence": self._count(conn, "raw_evidence"),
                "canonical_companies": self._count(conn, "canonical_companies"),
                "vendor_scores": self._count(conn, "vendor_scores"),
                "vendor_profiles": self._count(conn, "vendor_profiles"),
                "dedup_decisions": self._count(conn, "dedup_decisions"),
                "review_queue": self._count(conn, "review_queue"),
                "qualification_decisions": self._count(conn, "qualification_decisions"),
                "routing_audit": self._count(conn, "routing_audit"),
                "commercial_records": self._count(conn, "commercial_records"),
                "customer_accounts": self._count(conn, "customer_accounts"),
                "commercial_opportunities": self._count(conn, "commercial_opportunities"),
                "quote_intents": self._count(conn, "quote_intents"),
                "production_handoffs": self._count(conn, "production_handoffs"),
                "commercial_audit_log": self._count(conn, "commercial_audit_log"),
                "feedback_events": self._count(conn, "feedback_events"),
                "feedback_status_projection": self._count(conn, "feedback_status_projection"),
            }

    def list_raw_records(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Return persisted raw discovery rows for standalone API consumers."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM raw_records
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._decode_raw_record(dict(row)) for row in rows]

    def list_companies(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Return canonical companies owned by the standalone slice."""
        query = """
            SELECT *
            FROM canonical_companies
            ORDER BY id DESC
        """
        params: tuple[Any, ...]
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params = (limit, offset)
        else:
            params = ()
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._decode_company(dict(row)) for row in rows]

    def get_company_by_id(self, company_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM canonical_companies WHERE id = ?",
                (company_id,),
            ).fetchone()
        return None if row is None else self._decode_company(dict(row))

    def list_companies_by_keys(self, company_keys: list[str]) -> dict[str, dict[str, Any]]:
        if not company_keys:
            return {}
        normalized_keys = sorted({str(key).strip() for key in company_keys if str(key).strip()})
        if not normalized_keys:
            return {}
        placeholders = ", ".join(["?"] * len(normalized_keys))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM canonical_companies
                WHERE canonical_key IN ({placeholders})
                """,
                tuple(normalized_keys),
            ).fetchall()
        decoded = [self._decode_company(dict(row)) for row in rows]
        return {item["canonical_key"]: item for item in decoded}

    def list_scores(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Return standalone score rows."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM vendor_scores
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_score(self, company_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM vendor_scores WHERE company_key = ?",
                (company_key,),
            ).fetchone()
        return None if row is None else dict(row)

    def get_company_by_key(self, company_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM canonical_companies
                WHERE canonical_key = ?
                   OR source_fingerprint = ?
                   OR dedup_fingerprint = ?
                   OR website = ?
                LIMIT 1
                """,
                (company_key, company_key, company_key, company_key),
            ).fetchone()
        return None if row is None else self._decode_company(dict(row))

    def get_vendor_profile(self, company_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM vendor_profiles WHERE company_key = ?",
                (company_key,),
            ).fetchone()
        return None if row is None else self._decode_vendor_profile(dict(row))

    def list_vendor_profiles(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM vendor_profiles
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._decode_vendor_profile(dict(row)) for row in rows]

    def list_dedup_decisions(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Return persisted dedup decisions."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM dedup_decisions
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._decode_dedup_decision(dict(row)) for row in rows]

    def list_review_queue(self, limit: int = 100, offset: int = 0, company_key: str | None = None) -> list[dict[str, Any]]:
        """Return standalone review queue rows."""
        query = """
            SELECT *
            FROM review_queue
        """
        params: list[Any] = []
        if company_key:
            query += " WHERE company_key = ?"
            params.append(company_key)
        query += " ORDER BY priority DESC, id DESC"
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_review_queue(dict(row)) for row in rows]

    def get_review_queue(self, queue_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM review_queue WHERE id = ?", (queue_id,)).fetchone()
        return None if row is None else self._decode_review_queue(dict(row))

    def transition_review_queue(self, queue_id: int, target_status: str, reason_code: str, notes: str = "", allow_reprocess: bool = False, actor: str = "operator") -> bool:
        allowed_transitions = {
            "pending": {"in_progress", "done", "dismissed"},
            "in_progress": {"pending", "done", "dismissed"},
            "done": {"pending"},
            "dismissed": {"pending"},
        }
        with self._connect() as conn:
            queue = conn.execute("SELECT * FROM review_queue WHERE id = ?", (queue_id,)).fetchone()
            if queue is None:
                raise LookupError(f"queue:{queue_id}")
            source_status = queue["status"]
            if target_status not in allowed_transitions.get(source_status, set()):
                raise ValueError(f"invalid_transition:{source_status}->{target_status}")
            if source_status in {"done", "dismissed"} and target_status == "pending" and not allow_reprocess:
                raise ValueError("reprocess_requires_allow_reprocess")
            reprocess_count = int(queue["reprocess_count"] or 0)
            if source_status in {"done", "dismissed"} and target_status == "pending":
                reprocess_count += 1
            conn.execute(
                """
                UPDATE review_queue
                SET status = ?, reason_code = ?, reason = ?, reprocess_count = ?, last_transition_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (target_status, reason_code, notes or queue["reason"], reprocess_count, _utc_now(), _utc_now(), queue_id),
            )
            conn.execute(
                """
                INSERT INTO routing_audit (
                    company_key, queue_name, event_type, from_state, to_state, reason_code, evidence_refs_json,
                    notes, is_manual_override, actor, event_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    queue["company_key"],
                    queue["queue_name"],
                    "reprocess" if source_status in {"done", "dismissed"} and target_status == "pending" else "transition",
                    source_status,
                    target_status,
                    reason_code,
                    queue["evidence_refs_json"] or _json([]),
                    notes,
                    0,
                    actor,
                    _utc_now(),
                ),
            )
        return True

    def list_qualification_decisions(self, company_key: str | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        query = "SELECT * FROM qualification_decisions"
        params: list[Any] = []
        if company_key:
            query += " WHERE company_key = ?"
            params.append(company_key)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_qualification_decision(dict(row)) for row in rows]

    def list_routing_audit(self, company_key: str | None = None, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        query = "SELECT * FROM routing_audit"
        params: list[Any] = []
        if company_key:
            query += " WHERE company_key = ?"
            params.append(company_key)
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_routing_audit(dict(row)) for row in rows]

    def get_commercial_record(self, company_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM commercial_records WHERE company_key = ?",
                (company_key,),
            ).fetchone()
        return None if row is None else self._decode_commercial_record(dict(row))

    def list_commercial_records(
        self,
        limit: int = 100,
        offset: int = 0,
        stage: str | None = None,
        customer_status: str | None = None,
        company_key: str | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT *
            FROM commercial_records
        """
        params: list[Any] = []
        filters: list[str] = []
        if stage:
            filters.append("commercial_stage = ?")
            params.append(stage)
        if customer_status:
            filters.append("customer_status = ?")
            params.append(customer_status)
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY updated_at DESC, id DESC"
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_commercial_record(dict(row)) for row in rows]

    def count_commercial_records(self, stage: str | None = None, customer_status: str | None = None, company_key: str | None = None) -> int:
        query = "SELECT COUNT(*) AS count FROM commercial_records"
        params: list[Any] = []
        filters: list[str] = []
        if stage:
            filters.append("commercial_stage = ?")
            params.append(stage)
        if customer_status:
            filters.append("customer_status = ?")
            params.append(customer_status)
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        with self._connect() as conn:
            return int(conn.execute(query, tuple(params)).fetchone()["count"])

    def get_customer_account(self, company_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM customer_accounts WHERE company_key = ?",
                (company_key,),
            ).fetchone()
        return None if row is None else self._decode_customer_account(dict(row))

    def get_customer_account_by_id(self, account_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM customer_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        return None if row is None else self._decode_customer_account(dict(row))

    def upsert_customer_account(
        self,
        company_key: str,
        account_name: str,
        account_type: str = "direct_customer",
        account_status: str = "prospect",
        primary_contact_name: str = "",
        primary_email: str = "",
        primary_phone: str = "",
        billing_city: str = "",
        external_customer_ref: str = "",
        odoo_partner_ref: str = "",
        notes: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        company = self.get_company_by_key(company_key)
        if not company:
            raise LookupError(f"company_key:{company_key}")
        previous = self.get_customer_account(company_key)
        payload = {
            "company_key": company_key,
            "account_name": account_name,
            "account_type": account_type,
            "account_status": account_status,
            "primary_contact_name": primary_contact_name or "",
            "primary_email": primary_email or "",
            "primary_phone": primary_phone or "",
            "billing_city": billing_city or "",
            "external_customer_ref": external_customer_ref or "",
            "odoo_partner_ref": odoo_partner_ref or "",
            "notes": notes or "",
            "created_at": previous.get("created_at") if previous else _utc_now(),
            "updated_at": _utc_now(),
        }
        with self._connect() as conn:
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload.keys())
            updates = ", ".join(f"{key}=excluded.{key}" for key in payload.keys() if key not in {"company_key", "created_at"})
            conn.execute(
                f"""
                INSERT INTO customer_accounts ({columns})
                VALUES ({placeholders})
                ON CONFLICT(company_key) DO UPDATE SET {updates}
                """,
                payload,
            )
            row = conn.execute(
                "SELECT * FROM customer_accounts WHERE company_key = ?",
                (company_key,),
            ).fetchone()
            if row is None:
                raise LookupError(f"customer_account:{company_key}")
            record = self._decode_customer_account(dict(row))
            self._append_commercial_audit(
                conn,
                company_key=company_key,
                entity_type="customer_account",
                entity_id=int(record["id"]),
                action_type="upsert",
                previous_status=previous.get("account_status") if previous else None,
                new_status=record.get("account_status"),
                note=notes,
                actor=actor,
                metadata={
                    "account_type": record.get("account_type"),
                    "external_customer_ref": record.get("external_customer_ref"),
                },
            )
        return record

    def list_commercial_opportunities(
        self,
        company_key: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT *
            FROM commercial_opportunities
        """
        params: list[Any] = []
        filters: list[str] = []
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if status:
            filters.append("status = ?")
            params.append(status)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY updated_at DESC, id DESC"
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_commercial_opportunity(dict(row)) for row in rows]

    def count_commercial_opportunities(self, company_key: str | None = None, status: str | None = None) -> int:
        query = "SELECT COUNT(*) AS count FROM commercial_opportunities"
        params: list[Any] = []
        filters: list[str] = []
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if status:
            filters.append("status = ?")
            params.append(status)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        with self._connect() as conn:
            return int(conn.execute(query, tuple(params)).fetchone()["count"])

    def get_commercial_opportunity(self, opportunity_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM commercial_opportunities WHERE id = ?",
                (opportunity_id,),
            ).fetchone()
        return None if row is None else self._decode_commercial_opportunity(dict(row))

    def list_commercial_opportunities_by_ids(self, opportunity_ids: list[int]) -> dict[int, dict[str, Any]]:
        normalized_ids = sorted({int(item) for item in opportunity_ids if int(item) > 0})
        if not normalized_ids:
            return {}
        placeholders = ", ".join(["?"] * len(normalized_ids))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM commercial_opportunities WHERE id IN ({placeholders})",
                tuple(normalized_ids),
            ).fetchall()
        decoded = [self._decode_commercial_opportunity(dict(row)) for row in rows]
        return {int(item["id"]): item for item in decoded}

    def create_commercial_opportunity(
        self,
        company_key: str,
        customer_account_id: int | None,
        title: str,
        status: str,
        source_channel: str = "",
        estimated_value: float | None = None,
        currency_code: str = "VND",
        target_due_at: str = "",
        next_action: str = "",
        notes: str = "",
        external_opportunity_ref: str = "",
        odoo_lead_ref: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        company = self.get_company_by_key(company_key)
        if not company:
            raise LookupError(f"company_key:{company_key}")
        account = self._resolve_account_for_company(company_key, customer_account_id)
        payload = {
            "company_key": company_key,
            "customer_account_id": account.get("id") if account else None,
            "title": title,
            "status": status,
            "source_channel": source_channel or "",
            "estimated_value": estimated_value,
            "currency_code": currency_code or "VND",
            "target_due_at": target_due_at or "",
            "next_action": next_action or "",
            "notes": notes or "",
            "external_opportunity_ref": external_opportunity_ref or "",
            "odoo_lead_ref": odoo_lead_ref or "",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        with self._connect() as conn:
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload.keys())
            conn.execute(
                f"""
                INSERT INTO commercial_opportunities ({columns})
                VALUES ({placeholders})
                """,
                payload,
            )
            row_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            row = conn.execute("SELECT * FROM commercial_opportunities WHERE id = ?", (row_id,)).fetchone()
            if row is None:
                raise LookupError(f"commercial_opportunity:{company_key}")
            record = self._decode_commercial_opportunity(dict(row))
            self._append_commercial_audit(
                conn,
                company_key=company_key,
                entity_type="commercial_opportunity",
                entity_id=row_id,
                action_type="create",
                previous_status=None,
                new_status=status,
                note=notes,
                actor=actor,
                metadata={"title": title, "customer_account_id": payload["customer_account_id"]},
            )
        return record

    def update_commercial_opportunity(
        self,
        opportunity_id: int,
        title: str,
        status: str,
        customer_account_id: int | None = None,
        source_channel: str = "",
        estimated_value: float | None = None,
        currency_code: str = "VND",
        target_due_at: str = "",
        next_action: str = "",
        notes: str = "",
        external_opportunity_ref: str = "",
        odoo_lead_ref: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        existing = self.get_commercial_opportunity(opportunity_id)
        if existing is None:
            raise LookupError(f"commercial_opportunity:{opportunity_id}")
        account = self._resolve_account_for_company(existing["company_key"], customer_account_id)
        payload = {
            "id": opportunity_id,
            "title": title,
            "status": status,
            "customer_account_id": account.get("id") if account else None,
            "source_channel": source_channel or "",
            "estimated_value": estimated_value,
            "currency_code": currency_code or "VND",
            "target_due_at": target_due_at or "",
            "next_action": next_action or "",
            "notes": notes or "",
            "external_opportunity_ref": external_opportunity_ref or "",
            "odoo_lead_ref": odoo_lead_ref or "",
            "updated_at": _utc_now(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE commercial_opportunities
                SET title = :title,
                    status = :status,
                    customer_account_id = :customer_account_id,
                    source_channel = :source_channel,
                    estimated_value = :estimated_value,
                    currency_code = :currency_code,
                    target_due_at = :target_due_at,
                    next_action = :next_action,
                    notes = :notes,
                    external_opportunity_ref = :external_opportunity_ref,
                    odoo_lead_ref = :odoo_lead_ref,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                payload,
            )
            self._append_commercial_audit(
                conn,
                company_key=existing["company_key"],
                entity_type="commercial_opportunity",
                entity_id=opportunity_id,
                action_type="update",
                previous_status=existing.get("status"),
                new_status=status,
                note=notes,
                actor=actor,
                metadata={"title": title, "customer_account_id": payload["customer_account_id"]},
            )
        record = self.get_commercial_opportunity(opportunity_id)
        if record is None:
            raise LookupError(f"commercial_opportunity:{opportunity_id}")
        return record

    def list_commercial_audit(
        self,
        company_key: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM commercial_audit_log"
        params: list[Any] = []
        filters: list[str] = []
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if entity_type:
            filters.append("entity_type = ?")
            params.append(entity_type)
        if entity_id is not None:
            filters.append("entity_id = ?")
            params.append(entity_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY occurred_at DESC, id DESC"
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_commercial_audit(dict(row)) for row in rows]

    def list_quote_intents(
        self,
        company_key: str | None = None,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        quote_type: str | None = None,
        quote_intent_ids: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM quote_intents"
        params: list[Any] = []
        filters: list[str] = []
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if status:
            filters.append("status = ?")
            params.append(status)
        if quote_type:
            filters.append("quote_type = ?")
            params.append(quote_type)
        if quote_intent_ids is not None:
            normalized_ids = sorted({int(item) for item in quote_intent_ids if int(item) > 0})
            if not normalized_ids:
                return []
            placeholders = ", ".join(["?"] * len(normalized_ids))
            filters.append(f"id IN ({placeholders})")
            params.extend(normalized_ids)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_at DESC, id DESC"
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_quote_intent(dict(row)) for row in rows]

    def count_quote_intents(self, company_key: str | None = None, status: str | None = None, quote_type: str | None = None) -> int:
        query = "SELECT COUNT(*) AS count FROM quote_intents"
        params: list[Any] = []
        filters: list[str] = []
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if status:
            filters.append("status = ?")
            params.append(status)
        if quote_type:
            filters.append("quote_type = ?")
            params.append(quote_type)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        with self._connect() as conn:
            return int(conn.execute(query, tuple(params)).fetchone()["count"])

    def list_quote_intents_by_ids(self, quote_intent_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not quote_intent_ids:
            return {}
        rows = self.list_quote_intents(limit=0, quote_intent_ids=quote_intent_ids)
        return {int(item["id"]): item for item in rows if int(item.get("id") or 0) > 0}

    def get_quote_intent(self, quote_intent_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM quote_intents WHERE id = ?", (quote_intent_id,)).fetchone()
        return None if row is None else self._decode_quote_intent(dict(row))

    def list_production_handoffs(
        self,
        company_key: str | None = None,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        quote_intent_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM production_handoffs"
        params: list[Any] = []
        filters: list[str] = []
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if status:
            filters.append("handoff_status = ?")
            params.append(status)
        if quote_intent_id is not None:
            filters.append("quote_intent_id = ?")
            params.append(int(quote_intent_id))
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY updated_at DESC, id DESC"
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_production_handoff(dict(row)) for row in rows]

    def list_production_handoffs_by_quote_intent_ids(self, quote_intent_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not quote_intent_ids:
            return {}
        normalized_ids = sorted({int(item) for item in quote_intent_ids if int(item) > 0})
        if not normalized_ids:
            return {}
        placeholders = ", ".join(["?"] * len(normalized_ids))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM production_handoffs
                WHERE quote_intent_id IN ({placeholders})
                ORDER BY updated_at DESC, id DESC
                """,
                tuple(normalized_ids),
            ).fetchall()
        mapped: dict[int, dict[str, Any]] = {}
        for row in rows:
            decoded = self._decode_production_handoff(dict(row))
            quote_id = int(decoded.get("quote_intent_id") or 0)
            if quote_id > 0 and quote_id not in mapped:
                mapped[quote_id] = decoded
        return mapped

    def count_production_handoffs(self, company_key: str | None = None, status: str | None = None) -> int:
        query = "SELECT COUNT(*) AS count FROM production_handoffs"
        params: list[Any] = []
        filters: list[str] = []
        if company_key:
            filters.append("company_key = ?")
            params.append(company_key)
        if status:
            filters.append("handoff_status = ?")
            params.append(status)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        with self._connect() as conn:
            return int(conn.execute(query, tuple(params)).fetchone()["count"])

    def get_production_handoff(self, handoff_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM production_handoffs WHERE id = ?", (handoff_id,)).fetchone()
        return None if row is None else self._decode_production_handoff(dict(row))

    def create_quote_intent(
        self,
        company_key: str,
        quote_type: str,
        customer_account_id: int | None = None,
        opportunity_id: int | None = None,
        quantity_hint: str = "",
        target_due_at: str = "",
        status: str = "requested",
        rfq_reference: str = "",
        notes: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        company = self.get_company_by_key(company_key)
        if not company:
            raise LookupError(f"company_key:{company_key}")
        account, opportunity = self._resolve_commercial_links(company_key, customer_account_id, opportunity_id)
        payload = {
            "company_key": company_key,
            "customer_account_id": account.get("id") if account else None,
            "opportunity_id": opportunity.get("id") if opportunity else None,
            "quote_type": quote_type,
            "quantity_hint": quantity_hint or "",
            "target_due_at": target_due_at or "",
            "status": status,
            "rfq_reference": rfq_reference or "",
            "quote_reference": "",
            "quoted_amount": None,
            "currency_code": "VND",
            "pricing_notes": "",
            "last_status_at": _utc_now(),
            "notes": notes or "",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        with self._connect() as conn:
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload.keys())
            conn.execute(
                f"""
                INSERT INTO quote_intents ({columns})
                VALUES ({placeholders})
                """,
                payload,
            )
            row_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            row = conn.execute("SELECT * FROM quote_intents WHERE id = ?", (row_id,)).fetchone()
            if row is not None:
                self._append_commercial_audit(
                    conn,
                    company_key=company_key,
                    entity_type="quote_intent",
                    entity_id=row_id,
                    action_type="create",
                    previous_status=None,
                    new_status=status,
                    note=notes,
                    actor=actor,
                    metadata={
                        "quote_type": quote_type,
                        "customer_account_id": payload["customer_account_id"],
                        "opportunity_id": payload["opportunity_id"],
                        "rfq_reference": payload["rfq_reference"],
                    },
                )
        if row is None:
            raise LookupError(f"quote_intent:{company_key}")
        return self._decode_quote_intent(dict(row))

    def update_quote_intent(
        self,
        quote_intent_id: int,
        status: str,
        customer_account_id: int | None = None,
        opportunity_id: int | None = None,
        rfq_reference: str = "",
        quote_reference: str = "",
        quoted_amount: float | None = None,
        currency_code: str = "VND",
        target_due_at: str = "",
        pricing_notes: str = "",
        notes: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        existing = self.get_quote_intent(quote_intent_id)
        if existing is None:
            raise LookupError(f"quote_intent:{quote_intent_id}")
        fallback_account_id = customer_account_id if customer_account_id is not None else _optional_db_int(existing.get("customer_account_id"))
        fallback_opportunity_id = opportunity_id if opportunity_id is not None else _optional_db_int(existing.get("opportunity_id"))
        account, opportunity = self._resolve_commercial_links(existing["company_key"], fallback_account_id, fallback_opportunity_id)
        payload = {
            "status": status,
            "customer_account_id": account.get("id") if account else None,
            "opportunity_id": opportunity.get("id") if opportunity else None,
            "rfq_reference": rfq_reference or "",
            "quote_reference": quote_reference or "",
            "quoted_amount": quoted_amount,
            "currency_code": currency_code or "VND",
            "target_due_at": target_due_at or "",
            "pricing_notes": pricing_notes or "",
            "notes": notes or "",
            "last_status_at": _utc_now(),
            "updated_at": _utc_now(),
            "id": quote_intent_id,
        }
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE quote_intents
                SET status = :status,
                    customer_account_id = :customer_account_id,
                    opportunity_id = :opportunity_id,
                    rfq_reference = :rfq_reference,
                    quote_reference = :quote_reference,
                    quoted_amount = :quoted_amount,
                    currency_code = :currency_code,
                    target_due_at = :target_due_at,
                    pricing_notes = :pricing_notes,
                    notes = :notes,
                    last_status_at = :last_status_at,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                payload,
            )
            self._append_commercial_audit(
                conn,
                company_key=existing["company_key"],
                entity_type="quote_intent",
                entity_id=quote_intent_id,
                action_type="update",
                previous_status=existing.get("status"),
                new_status=status,
                note=notes,
                actor=actor,
                metadata={
                    "customer_account_id": payload["customer_account_id"],
                    "opportunity_id": payload["opportunity_id"],
                    "rfq_reference": payload["rfq_reference"],
                    "quote_reference": payload["quote_reference"],
                },
            )
        record = self.get_quote_intent(quote_intent_id)
        if record is None:
            raise LookupError(f"quote_intent:{quote_intent_id}")
        return record

    def create_production_handoff(
        self,
        company_key: str,
        quote_intent_id: int | None = None,
        handoff_status: str = "ready_for_production",
        production_reference: str = "",
        requested_ship_at: str = "",
        specification_summary: str = "",
        notes: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        company = self.get_company_by_key(company_key)
        if not company:
            raise LookupError(f"company_key:{company_key}")
        linked_quote: dict[str, Any] | None = None
        if quote_intent_id is not None:
            linked_quote = self.get_quote_intent(quote_intent_id)
            if linked_quote is None:
                raise LookupError(f"quote_intent:{quote_intent_id}")
            if linked_quote.get("company_key") != company_key:
                raise ValueError("quote_intent_company_mismatch")
        payload = {
            "company_key": company_key,
            "quote_intent_id": quote_intent_id,
            "handoff_status": handoff_status,
            "production_reference": production_reference or "",
            "requested_ship_at": requested_ship_at or "",
            "specification_summary": specification_summary or "",
            "notes": notes or "",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        with self._connect() as conn:
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload.keys())
            conn.execute(
                f"""
                INSERT INTO production_handoffs ({columns})
                VALUES ({placeholders})
                """,
                payload,
            )
            row_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            row = conn.execute("SELECT * FROM production_handoffs WHERE id = ?", (row_id,)).fetchone()
            if row is not None:
                self._append_commercial_audit(
                    conn,
                    company_key=company_key,
                    entity_type="production_handoff",
                    entity_id=row_id,
                    action_type="create",
                    previous_status=None,
                    new_status=handoff_status,
                    note=notes,
                    actor=actor,
                    metadata={"quote_intent_id": quote_intent_id, "production_reference": production_reference or ""},
                )
        if row is None:
            raise LookupError(f"production_handoff:{company_key}")
        return self._decode_production_handoff(dict(row))

    def update_production_handoff(
        self,
        handoff_id: int,
        handoff_status: str,
        production_reference: str | None = None,
        requested_ship_at: str | None = None,
        specification_summary: str | None = None,
        notes: str | None = None,
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        existing = self.get_production_handoff(handoff_id)
        if existing is None:
            raise LookupError(f"production_handoff:{handoff_id}")
        payload = {
            "handoff_status": handoff_status,
            "production_reference": existing.get("production_reference") if production_reference is None else production_reference,
            "requested_ship_at": existing.get("requested_ship_at") if requested_ship_at is None else requested_ship_at,
            "specification_summary": existing.get("specification_summary") if specification_summary is None else specification_summary,
            "notes": existing.get("notes") if notes is None else notes,
            "updated_at": _utc_now(),
            "id": handoff_id,
        }
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE production_handoffs
                SET handoff_status = :handoff_status,
                    production_reference = :production_reference,
                    requested_ship_at = :requested_ship_at,
                    specification_summary = :specification_summary,
                    notes = :notes,
                    updated_at = :updated_at
                WHERE id = :id
                """,
                payload,
            )
            self._append_commercial_audit(
                conn,
                company_key=existing["company_key"],
                entity_type="production_handoff",
                entity_id=handoff_id,
                action_type="update",
                previous_status=existing.get("handoff_status"),
                new_status=handoff_status,
                note=payload["notes"],
                actor=actor,
                metadata={"quote_intent_id": existing.get("quote_intent_id"), "production_reference": payload["production_reference"]},
            )
        record = self.get_production_handoff(handoff_id)
        if record is None:
            raise LookupError(f"production_handoff:{handoff_id}")
        return record

    def upsert_commercial_record(
        self,
        company_key: str,
        customer_status: str,
        commercial_stage: str,
        customer_reference: str = "",
        opportunity_reference: str = "",
        next_action: str = "",
        next_action_due_at: str = "",
        notes: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        company = self.get_company_by_key(company_key)
        if not company:
            raise LookupError(f"company_key:{company_key}")
        previous = self.get_commercial_record(company_key)
        payload = {
            "company_key": company_key,
            "customer_status": customer_status,
            "commercial_stage": commercial_stage,
            "customer_reference": customer_reference or "",
            "opportunity_reference": opportunity_reference or "",
            "next_action": next_action or "",
            "next_action_due_at": next_action_due_at or "",
            "notes": notes or "",
            "updated_at": _utc_now(),
        }
        with self._connect() as conn:
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload.keys())
            updates = ", ".join(f"{key}=excluded.{key}" for key in payload.keys() if key != "company_key")
            conn.execute(
                f"""
                INSERT INTO commercial_records ({columns})
                VALUES ({placeholders})
                ON CONFLICT(company_key) DO UPDATE SET {updates}
                """,
                payload,
            )
            row = conn.execute("SELECT * FROM commercial_records WHERE company_key = ?", (company_key,)).fetchone()
            if row is None:
                raise LookupError(f"commercial_record:{company_key}")
            record = self._decode_commercial_record(dict(row))
            self._append_commercial_audit(
                conn,
                company_key=company_key,
                entity_type="commercial_record",
                entity_id=int(record["id"]),
                action_type="upsert",
                previous_status=previous.get("commercial_stage") if previous else None,
                new_status=record.get("commercial_stage"),
                note=notes,
                actor=actor,
                metadata={"customer_status": customer_status},
            )
        return record

    def _resolve_account_for_company(self, company_key: str, customer_account_id: int | None) -> dict[str, Any] | None:
        if customer_account_id is None:
            return None
        account = self.get_customer_account_by_id(customer_account_id)
        if account is None:
            raise LookupError(f"customer_account:{customer_account_id}")
        if account.get("company_key") != company_key:
            raise ValueError("customer_account_company_mismatch")
        return account

    def _resolve_commercial_links(
        self,
        company_key: str,
        customer_account_id: int | None,
        opportunity_id: int | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        account = self._resolve_account_for_company(company_key, customer_account_id)
        opportunity: dict[str, Any] | None = None
        if opportunity_id is not None:
            opportunity = self.get_commercial_opportunity(opportunity_id)
            if opportunity is None:
                raise LookupError(f"commercial_opportunity:{opportunity_id}")
            if opportunity.get("company_key") != company_key:
                raise ValueError("opportunity_company_mismatch")
            linked_account_id = _optional_db_int(opportunity.get("customer_account_id"))
            if account is not None and linked_account_id is not None and linked_account_id != int(account["id"]):
                raise ValueError("opportunity_customer_account_mismatch")
            if account is None and linked_account_id is not None:
                account = self.get_customer_account_by_id(linked_account_id)
        return account, opportunity

    def _append_commercial_audit(
        self,
        conn: sqlite3.Connection,
        company_key: str,
        entity_type: str,
        entity_id: int,
        action_type: str,
        previous_status: str | None,
        new_status: str | None,
        note: str | None,
        actor: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        conn.execute(
            """
            INSERT INTO commercial_audit_log (
                company_key, entity_type, entity_id, action_type,
                previous_status, new_status, note, actor, metadata_json, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_key,
                entity_type,
                entity_id,
                action_type,
                previous_status or "",
                new_status or "",
                note or "",
                actor or "",
                _json(metadata or {}),
                _utc_now(),
            ),
        )

    def get_pending_dedup_signal(self, company_key: str) -> tuple[bool, float]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT confidence
                FROM dedup_decisions
                WHERE decision = 'needs_manual_review'
                  AND (left_company_key = ? OR right_company_key = ?)
                ORDER BY confidence DESC, id DESC
                LIMIT 1
                """,
                (company_key, company_key),
            ).fetchall()
        if not rows:
            return False, 0.0
        return True, float(rows[0]["confidence"] or 0.0)

    def apply_routing_decision(
        self,
        company_key: str,
        outcome: RoutingOutcome,
        reason_code: str,
        evidence_refs: list[str],
        notes: str,
        manual_override: bool,
    ) -> RoutingDecisionResult:
        company = self.get_company_by_key(company_key)
        if not company:
            raise LookupError(f"company_key:{company_key}")
        score_row = self.get_score(company["canonical_key"])
        profile = self.get_vendor_profile(company["canonical_key"])
        if not score_row:
            raise ValueError(f"missing_score:{company_key}")

        score = float((profile or {}).get("composite_score") or score_row.get("composite_score") or company.get("confidence") or 0.0)
        contactability_score = float((profile or {}).get("contactability_score") or score_row.get("contactability_score") or 0.0)
        capability_fit_score = float((profile or {}).get("capability_fit_score") or score_row.get("capability_fit_score") or 0.0)
        outreach_ready = outcome in {"approved_supplier", "potential_supplier"} and contactability_score >= 0.6
        rfq_ready = outcome == "approved_supplier" and capability_fit_score >= 0.6
        review_status, qualification_status, lifecycle_state = outcome_profile_state(outcome)
        queue_name = queue_for_outcome(outcome)
        previous_state = (profile or {}).get("routing_state") or "unreviewed"

        with self._connect() as conn:
            profile_row = conn.execute("SELECT * FROM vendor_profiles WHERE company_key = ?", (company["canonical_key"],)).fetchone()
            profile_payload = {
                "company_key": company["canonical_key"],
                "review_status": review_status,
                "qualification_status": qualification_status,
                "relevance_score": float((profile or {}).get("relevance_score") or score_row.get("relevance_score") or 0.0),
                "capability_fit_score": capability_fit_score,
                "contactability_score": contactability_score,
                "freshness_score": float((profile or {}).get("freshness_score") or score_row.get("freshness_score") or 0.0),
                "trust_score": float((profile or {}).get("trust_score") or score_row.get("trust_score") or 0.0),
                "composite_score": score,
                "parser_confidence": float((profile or {}).get("parser_confidence") or score_row.get("parser_confidence") or 0.0),
                "outreach_ready": 1 if outreach_ready else 0,
                "rfq_ready": 1 if rfq_ready else 0,
                "lifecycle_state": lifecycle_state,
                "routing_state": outcome,
                "notes": notes or ((profile or {}).get("notes") or ""),
                "last_routed_at": _utc_now(),
                "updated_at": _utc_now(),
            }
            columns = ", ".join(profile_payload.keys())
            placeholders = ", ".join(f":{key}" for key in profile_payload.keys())
            updates = ", ".join(f"{key}=excluded.{key}" for key in profile_payload.keys() if key != "company_key")
            conn.execute(
                f"""
                INSERT INTO vendor_profiles ({columns})
                VALUES ({placeholders})
                ON CONFLICT(company_key) DO UPDATE SET {updates}
                """,
                profile_payload,
            )
            profile_id = conn.execute("SELECT id FROM vendor_profiles WHERE company_key = ?", (company["canonical_key"],)).fetchone()["id"]
            decision_payload = {
                "company_key": company["canonical_key"],
                "vendor_profile_id": profile_id,
                "decision": "approve" if outcome in {"approved_supplier", "potential_supplier"} else "needs_info" if outcome == "needs_manual_review" else "reject",
                "route_outcome": outcome,
                "reason_code": reason_code or "routing_rule",
                "evidence_refs_json": _json(evidence_refs),
                "internal_note": notes or "",
                "reprocess_token": _utc_now(),
                "decision_confidence": score,
                "rationale": notes or reason_code or "Rule-based routing decision",
                "algorithm_version": "routing_v1",
                "decision_at": _utc_now(),
                "decided_by": "standalone_operator" if manual_override else "standalone_engine",
                "is_manual_override": 1 if manual_override else 0,
            }
            columns = ", ".join(decision_payload.keys())
            placeholders = ", ".join(f":{key}" for key in decision_payload.keys())
            conn.execute(
                f"""
                INSERT INTO qualification_decisions ({columns})
                VALUES ({placeholders})
                """,
                decision_payload,
            )
            decision_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
            queue = conn.execute(
                """
                SELECT *
                FROM review_queue
                WHERE company_key = ? AND queue_name = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (company["canonical_key"], queue_name),
            ).fetchone()
            queue_payload = {
                "company_key": company["canonical_key"],
                "queue_name": queue_name,
                "priority": 95 if outcome == "approved_supplier" else 70 if outcome == "potential_supplier" else 50,
                "reason": notes or reason_code,
                "reason_code": reason_code or "routing_rule",
                "evidence_refs_json": _json(evidence_refs),
                "score": score,
                "status": "pending" if outcome == "needs_manual_review" else "done",
                "reprocess_count": int(queue["reprocess_count"] or 0) if queue else 0,
                "last_transition_at": _utc_now(),
                "updated_at": _utc_now(),
            }
            columns = ", ".join(queue_payload.keys())
            placeholders = ", ".join(f":{key}" for key in queue_payload.keys())
            updates = ", ".join(f"{key}=excluded.{key}" for key in queue_payload.keys() if key not in {"company_key", "queue_name"})
            conn.execute(
                f"""
                INSERT INTO review_queue ({columns})
                VALUES ({placeholders})
                ON CONFLICT(company_key, queue_name) DO UPDATE SET {updates}
                """,
                queue_payload,
            )
            conn.execute(
                """
                INSERT INTO routing_audit (
                    company_key, queue_name, vendor_profile_id, qualification_decision_id, event_type,
                    from_state, to_state, reason_code, evidence_refs_json, notes, is_manual_override, actor, event_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company["canonical_key"],
                    queue_name,
                    profile_id,
                    decision_id,
                    "override" if manual_override else "routed",
                    previous_state,
                    outcome,
                    reason_code or "routing_rule",
                    _json(evidence_refs),
                    notes,
                    1 if manual_override else 0,
                    "standalone_operator" if manual_override else "standalone_engine",
                    _utc_now(),
                ),
            )
        return RoutingDecisionResult(
            company_key=company["canonical_key"],
            outcome=outcome,
            reason_code=reason_code or "routing_rule",
            queue_name=queue_name,
            score=score,
            outreach_ready=outreach_ready,
            rfq_ready=rfq_ready,
        )

    def list_feedback_events(
        self,
        limit: int = 100,
        offset: int = 0,
        source_key: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return downstream Odoo-originated feedback events applied into standalone state."""
        query = """
            SELECT *
            FROM feedback_events
        """
        params: list[Any] = []
        filters: list[str] = []
        if source_key:
            filters.append("source_key = ?")
            params.append(source_key)
        if event_type:
            filters.append("event_type = ?")
            params.append(event_type)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY id DESC"
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_feedback_event(dict(row)) for row in rows]

    def list_feedback_status_by_source_keys(self, source_keys: list[str]) -> dict[str, FeedbackStatusProjection]:
        if not source_keys:
            return {}
        normalized_keys = sorted({str(key).strip() for key in source_keys if str(key).strip()})
        if not normalized_keys:
            return {}
        placeholders = ", ".join(["?"] * len(normalized_keys))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM feedback_status_projection
                WHERE source_key IN ({placeholders})
                """,
                tuple(normalized_keys),
            ).fetchall()
        items = [self._decode_feedback_status(dict(row)) for row in rows]
        return {item["source_key"]: item for item in items}

    def list_raw_records_linked(
        self,
        source_fingerprint: str = "",
        dedup_fingerprint: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT *
            FROM raw_records
            WHERE source_fingerprint = ?
               OR (? != '' AND candidate_dedup_fingerprint = ?)
            ORDER BY id DESC
        """
        params: list[Any] = [source_fingerprint or "", dedup_fingerprint or "", dedup_fingerprint or ""]
        if limit > 0:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._decode_raw_record(dict(row)) for row in rows]

    def list_feedback_status(self, limit: int = 100, offset: int = 0) -> list[FeedbackStatusProjection]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM feedback_status_projection
                ORDER BY updated_at DESC, source_key ASC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._decode_feedback_status(dict(row)) for row in rows]

    def get_feedback_status(self, source_key: str) -> FeedbackStatusProjection | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM feedback_status_projection
                WHERE source_key = ?
                """,
                (source_key,),
            ).fetchone()
        return None if row is None else self._decode_feedback_status(dict(row))

    @staticmethod
    def _count(conn: sqlite3.Connection, table: str) -> int:
        return int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])

    @staticmethod
    def _decode_json(value: str | None, default: Any) -> Any:
        if not value:
            return default
        return json.loads(value)

    @classmethod
    def _decode_raw_record(cls, row: dict[str, Any]) -> dict[str, Any]:
        categories = cls._decode_json(row.pop("categories_json", "[]"), [])
        services = cls._decode_json(row.pop("services_json", "[]"), [])
        products = cls._decode_json(row.pop("products_json", "[]"), [])
        labels = cls._decode_json(row.pop("labels_json", "[]"), [])
        phones = cls._decode_json(row.pop("phones_json", "[]"), [])
        emails = cls._decode_json(row.pop("emails_json", "[]"), [])
        contact_persons = cls._decode_json(row.pop("contact_persons_json", "[]"), [])
        messengers = cls._decode_json(row.pop("messengers_json", "[]"), [])
        social_links = cls._decode_json(row.pop("social_links_json", "[]"), [])
        languages = cls._decode_json(row.pop("languages_json", "[]"), [])
        execution_reasons = cls._decode_json(row.pop("execution_reasons_json", "[]"), [])
        execution_flags = cls._decode_json(row.pop("execution_flags_json", "{}"), {})
        raw_payload = cls._decode_json(row.pop("raw_payload_json", "{}"), {})
        raw_evidence_refs = cls._decode_json(row.pop("raw_evidence_refs_json", "[]"), [])
        return {
            **row,
            "categories": categories,
            "services": services,
            "products": products,
            "labels": labels,
            "phones": phones,
            "emails": emails,
            "contact_persons": contact_persons,
            "messengers": messengers,
            "social_links": social_links,
            "languages": languages,
            "execution_reasons": execution_reasons,
            "execution_flags": execution_flags,
            "raw_payload": raw_payload,
            "raw_evidence_refs": raw_evidence_refs,
        }

    @classmethod
    def _decode_company(cls, row: dict[str, Any]) -> dict[str, Any]:
        capabilities = cls._decode_json(row.pop("capabilities_json", "[]"), [])
        provenance = cls._decode_json(row.pop("provenance_json", "[]"), [])
        return {
            **row,
            "capabilities": capabilities,
            "provenance": provenance,
        }

    @classmethod
    def _decode_dedup_decision(cls, row: dict[str, Any]) -> dict[str, Any]:
        match_signals = cls._decode_json(row.pop("match_signals_json", "[]"), [])
        return {
            **row,
            "match_signals": match_signals,
        }

    @classmethod
    def _decode_vendor_profile(cls, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "outreach_ready": bool(row.get("outreach_ready")),
            "rfq_ready": bool(row.get("rfq_ready")),
        }

    @classmethod
    def _decode_review_queue(cls, row: dict[str, Any]) -> dict[str, Any]:
        evidence_refs = cls._decode_json(row.pop("evidence_refs_json", "[]"), [])
        return {
            **row,
            "evidence_refs": evidence_refs,
        }

    @classmethod
    def _decode_qualification_decision(cls, row: dict[str, Any]) -> dict[str, Any]:
        evidence_refs = cls._decode_json(row.pop("evidence_refs_json", "[]"), [])
        return {
            **row,
            "evidence_refs": evidence_refs,
            "is_manual_override": bool(row.get("is_manual_override")),
        }

    @classmethod
    def _decode_routing_audit(cls, row: dict[str, Any]) -> dict[str, Any]:
        evidence_refs = cls._decode_json(row.pop("evidence_refs_json", "[]"), [])
        return {
            **row,
            "evidence_refs": evidence_refs,
            "is_manual_override": bool(row.get("is_manual_override")),
        }

    @classmethod
    def _decode_feedback_event(cls, row: dict[str, Any]) -> dict[str, Any]:
        payload = cls._decode_json(row.pop("payload_json", "{}"), {})
        return {
            **row,
            "partner_linked": bool(row.get("partner_linked")),
            "crm_linked": bool(row.get("crm_linked")),
            "is_manual_override": bool(row.get("is_manual_override")),
            "is_synthetic": bool(row.get("is_synthetic")),
            "payload": payload,
        }

    @classmethod
    def _decode_feedback_status(cls, row: dict[str, Any]) -> FeedbackStatusProjection:
        return {
            **row,
            "last_event_is_synthetic": bool(row.get("last_event_is_synthetic")),
            "routing_is_manual_override": bool(row.get("routing_is_manual_override")),
            "routing_is_synthetic": bool(row.get("routing_is_synthetic")),
            "qualification_is_manual_override": bool(row.get("qualification_is_manual_override")),
            "qualification_is_synthetic": bool(row.get("qualification_is_synthetic")),
            "partner_linked": bool(row.get("partner_linked")),
            "partner_is_synthetic": bool(row.get("partner_is_synthetic")),
            "crm_linked": bool(row.get("crm_linked")),
            "commercial_is_manual_override": bool(row.get("commercial_is_manual_override")),
            "commercial_is_synthetic": bool(row.get("commercial_is_synthetic")),
        }

    @classmethod
    def _decode_commercial_record(cls, row: dict[str, Any]) -> dict[str, Any]:
        return dict(row)

    @classmethod
    def _decode_customer_account(cls, row: dict[str, Any]) -> dict[str, Any]:
        return dict(row)

    @classmethod
    def _decode_commercial_opportunity(cls, row: dict[str, Any]) -> dict[str, Any]:
        return dict(row)

    @classmethod
    def _decode_commercial_audit(cls, row: dict[str, Any]) -> dict[str, Any]:
        metadata = cls._decode_json(row.pop("metadata_json", "{}"), {})
        return {**row, "metadata": metadata}

    @classmethod
    def _decode_quote_intent(cls, row: dict[str, Any]) -> dict[str, Any]:
        return dict(row)

    @classmethod
    def _decode_production_handoff(cls, row: dict[str, Any]) -> dict[str, Any]:
        return dict(row)

    def _apply_feedback_projection(self, conn: sqlite3.Connection, event: FeedbackEventPayload) -> None:
        existing_row = conn.execute(
            "SELECT * FROM feedback_status_projection WHERE source_key = ?",
            (event.source_key,),
        ).fetchone()
        payload: dict[str, Any]
        if existing_row is None:
            payload = self._empty_feedback_projection(event.source_key)
        else:
            payload = dict(existing_row)

        payload["source_key"] = event.source_key
        payload["company_id"] = event.company_id or payload.get("company_id")
        payload["vendor_profile_id"] = event.vendor_profile_id or payload.get("vendor_profile_id")

        if self._is_newer_feedback_event(payload.get("last_event_at"), event.occurred_at):
            payload["last_event_id"] = event.event_id
            payload["last_event_type"] = event.event_type
            payload["last_event_at"] = event.occurred_at
            payload["last_event_is_synthetic"] = 1 if event.is_synthetic else 0

        if event.event_type == "routing_feedback" and self._is_newer_feedback_event(payload.get("routing_occurred_at"), event.occurred_at):
            payload.update(
                {
                    "routing_event_id": event.event_id,
                    "routing_outcome": event.routing_outcome or "",
                    "manual_review_status": event.manual_review_status or "",
                    "routing_reason_code": event.reason_code or "",
                    "routing_notes": event.notes or "",
                    "routing_is_manual_override": 1 if event.is_manual_override else 0,
                    "routing_is_synthetic": 1 if event.is_synthetic else 0,
                    "routing_occurred_at": event.occurred_at,
                }
            )
        elif event.event_type == "qualification_feedback" and self._is_newer_feedback_event(
            payload.get("qualification_occurred_at"),
            event.occurred_at,
        ):
            payload.update(
                {
                    "qualification_event_id": event.event_id,
                    "qualification_decision_id": event.qualification_decision_id,
                    "qualification_status": event.qualification_status or "",
                    "qualification_reason_code": event.reason_code or "",
                    "qualification_notes": event.notes or "",
                    "qualification_is_manual_override": 1 if event.is_manual_override else 0,
                    "qualification_is_synthetic": 1 if event.is_synthetic else 0,
                    "qualification_occurred_at": event.occurred_at,
                }
            )
        elif event.event_type == "partner_linkage_feedback" and self._is_newer_feedback_event(
            payload.get("partner_occurred_at"),
            event.occurred_at,
        ):
            payload.update(
                {
                    "partner_linkage_event_id": event.event_id,
                    "partner_id": event.partner_id,
                    "partner_linked": 1 if event.partner_linked else 0,
                    "partner_is_synthetic": 1 if event.is_synthetic else 0,
                    "partner_occurred_at": event.occurred_at,
                }
            )
        elif event.event_type == "commercial_disposition_feedback" and self._is_newer_feedback_event(
            payload.get("commercial_occurred_at"),
            event.occurred_at,
        ):
            payload.update(
                {
                    "commercial_event_id": event.event_id,
                    "crm_lead_id": event.crm_lead_id,
                    "lead_mapping_id": event.lead_mapping_id,
                    "lead_status": event.lead_status or "",
                    "crm_linked": 1 if event.crm_linked else 0,
                    "commercial_reason_code": event.reason_code or "",
                    "commercial_notes": event.notes or "",
                    "commercial_is_manual_override": 1 if event.is_manual_override else 0,
                    "commercial_is_synthetic": 1 if event.is_synthetic else 0,
                    "commercial_occurred_at": event.occurred_at,
                }
            )

        payload["updated_at"] = _utc_now()
        columns = ", ".join(payload.keys())
        placeholders = ", ".join(f":{key}" for key in payload.keys())
        updates = ", ".join(f"{key}=excluded.{key}" for key in payload.keys() if key != "source_key")
        conn.execute(
            f"""
            INSERT INTO feedback_status_projection ({columns})
            VALUES ({placeholders})
            ON CONFLICT(source_key) DO UPDATE SET {updates}
            """,
            payload,
        )

    @staticmethod
    def _empty_feedback_projection(source_key: str) -> dict[str, Any]:
        return {
            "source_key": source_key,
            "company_id": None,
            "vendor_profile_id": None,
            "last_event_id": None,
            "last_event_type": None,
            "last_event_at": None,
            "last_event_is_synthetic": 0,
            "routing_event_id": None,
            "routing_outcome": "",
            "manual_review_status": "",
            "routing_reason_code": "",
            "routing_notes": "",
            "routing_is_manual_override": 0,
            "routing_is_synthetic": 0,
            "routing_occurred_at": None,
            "qualification_event_id": None,
            "qualification_decision_id": None,
            "qualification_status": "",
            "qualification_reason_code": "",
            "qualification_notes": "",
            "qualification_is_manual_override": 0,
            "qualification_is_synthetic": 0,
            "qualification_occurred_at": None,
            "partner_linkage_event_id": None,
            "partner_id": None,
            "partner_linked": 0,
            "partner_is_synthetic": 0,
            "partner_occurred_at": None,
            "commercial_event_id": None,
            "crm_lead_id": None,
            "lead_mapping_id": None,
            "lead_status": "",
            "crm_linked": 0,
            "commercial_reason_code": "",
            "commercial_notes": "",
            "commercial_is_manual_override": 0,
            "commercial_is_synthetic": 0,
            "commercial_occurred_at": None,
            "updated_at": _utc_now(),
        }

    @staticmethod
    def _is_newer_feedback_event(existing_at: str | None, candidate_at: str) -> bool:
        if not existing_at:
            return True
        return SqliteSupplierIntelligenceStore._feedback_time_key(candidate_at) >= SqliteSupplierIntelligenceStore._feedback_time_key(existing_at)

    @staticmethod
    def _feedback_time_key(value: str) -> str:
        if not value:
            return ""
        normalized = value.strip().replace("Z", "+00:00")
        if "T" not in normalized and " " in normalized:
            normalized = normalized.replace(" ", "T", 1)
        try:
            return datetime.fromisoformat(normalized).astimezone().isoformat()
        except ValueError:
            return normalized

    def _upsert_evidence(self, conn: sqlite3.Connection, row_id: int, item: RawCompanyRecord) -> None:
        for evidence in item.get("evidence_payloads") or []:
            payload = {
                "raw_record_id": row_id,
                "evidence_ref": evidence.get("evidence_ref") or "",
                "source_url": evidence.get("source_url") or "",
                "scenario_key": evidence.get("scenario_key") or "",
                "evidence_type": evidence.get("evidence_type") or "",
                "selector": evidence.get("selector") or "",
                "content": evidence.get("content") or "",
                "metadata_json": _json(evidence.get("metadata") or {}),
            }
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(f":{key}" for key in payload.keys())
            updates = ", ".join(
                f"{key}=excluded.{key}"
                for key in payload.keys()
                if key not in {"raw_record_id", "evidence_ref", "source_url", "evidence_type"}
            )
            conn.execute(
                f"""
                INSERT INTO raw_evidence ({columns})
                VALUES ({placeholders})
                ON CONFLICT(raw_record_id, evidence_ref, source_url, evidence_type) DO UPDATE SET {updates}
                """,
                payload,
            )

    @staticmethod
    def _raw_row(item: RawCompanyRecord) -> dict[str, Any]:
        return {
            "source_fingerprint": item.get("source_fingerprint") or "",
            "candidate_dedup_fingerprint": item.get("candidate_dedup_fingerprint") or "",
            "source_type": item.get("source_type") or "",
            "source_url": item.get("source_url") or "",
            "source_page_type": item.get("source_page_type") or "",
            "source_domain": item.get("source_domain") or "",
            "external_id": item.get("external_id") or "",
            "supplier_id": item.get("supplier_id") or "",
            "company_name": item.get("company_name") or "",
            "legal_name": item.get("legal_name") or "",
            "brand_alias": item.get("brand_alias") or "",
            "supplier_type": item.get("supplier_type") or "",
            "address_text": item.get("address_text") or "",
            "region": item.get("region") or "",
            "city": item.get("city") or "",
            "district": item.get("district") or "",
            "country": item.get("country") or "",
            "phone": item.get("phone") or "",
            "email": item.get("email") or "",
            "website": item.get("website") or "",
            "domain": item.get("domain") or "",
            "min_order": item.get("min_order") or "",
            "capabilities_text": item.get("capabilities_text") or "",
            "fetch_status": item.get("fetch_status") or "",
            "parser_confidence": float(item.get("parser_confidence") or 0.0),
            "source_confidence": float(item.get("source_confidence") or 0.0),
            "extraction_method": item.get("extraction_method") or "",
            "extraction_confidence": float(item.get("extraction_confidence") or 0.0),
            "scenario_key": item.get("scenario_key") or "",
            "escalation_count": int(item.get("escalation_count") or 0),
            "fetched_at": item.get("fetched_at") or "",
            "discovered_at": item.get("discovered_at") or "",
            "extracted_at": item.get("extracted_at") or "",
            "normalized_at": item.get("normalized_at") or "",
            "categories_json": _json(item.get("categories") or []),
            "services_json": _json(item.get("services") or []),
            "products_json": _json(item.get("products") or []),
            "labels_json": _json(item.get("labels") or []),
            "phones_json": _json(item.get("phones") or []),
            "emails_json": _json(item.get("emails") or []),
            "contact_persons_json": _json(item.get("contact_persons") or []),
            "messengers_json": _json(item.get("messengers") or []),
            "social_links_json": _json(item.get("social_links") or []),
            "languages_json": _json(item.get("languages") or []),
            "execution_reasons_json": _json(item.get("execution_reasons") or []),
            "execution_flags_json": _json(item.get("execution_flags") or {}),
            "raw_payload_json": _json(item.get("raw_payload") or {}),
            "raw_evidence_refs_json": _json(item.get("raw_evidence_refs") or []),
            "updated_at": _utc_now(),
        }

    @staticmethod
    def _company_row(item: NormalizedCompanyRecord) -> dict[str, Any]:
        return {
            "canonical_key": item["canonical_key"],
            "canonical_name": item.get("canonical_name") or "",
            "legal_name": item.get("legal_name") or "",
            "brand_alias": item.get("brand_alias") or "",
            "canonical_phone": item.get("canonical_phone") or "",
            "canonical_email": item.get("canonical_email") or "",
            "website": item.get("website") or "",
            "address_text": item.get("address_text") or "",
            "city": item.get("city") or "",
            "district": item.get("district") or "",
            "country_code": item.get("country_code") or "",
            "registration_code": item.get("registration_code") or "",
            "capabilities_json": _json(item.get("capabilities") or []),
            "confidence": float(item.get("confidence") or 0.0),
            "parser_confidence": float(item.get("parser_confidence") or 0.0),
            "source_confidence": float(item.get("source_confidence") or 0.0),
            "normalized_at": item.get("normalized_at") or "",
            "provenance_json": _json(item.get("provenance") or []),
            "review_status": item.get("review_status") or "",
            "source_fingerprint": item.get("source_fingerprint") or "",
            "dedup_fingerprint": item.get("dedup_fingerprint") or "",
            "updated_at": _utc_now(),
        }
