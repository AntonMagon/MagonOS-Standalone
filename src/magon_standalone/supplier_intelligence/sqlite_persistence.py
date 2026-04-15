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
    VendorProfileScorePayload,
    validate_feedback_event,
)
from .interfaces import SupplierIntelligencePersistence


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False, sort_keys=True)


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
                    score REAL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    updated_at TEXT NOT NULL,
                    UNIQUE(company_key, queue_name)
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
                    routing_event_id TEXT,
                    routing_outcome TEXT,
                    manual_review_status TEXT,
                    routing_reason_code TEXT,
                    routing_notes TEXT,
                    routing_is_manual_override INTEGER NOT NULL DEFAULT 0,
                    routing_occurred_at TEXT,
                    qualification_event_id TEXT,
                    qualification_decision_id INTEGER,
                    qualification_status TEXT,
                    qualification_reason_code TEXT,
                    qualification_notes TEXT,
                    qualification_is_manual_override INTEGER NOT NULL DEFAULT 0,
                    qualification_occurred_at TEXT,
                    partner_linkage_event_id TEXT,
                    partner_id INTEGER,
                    partner_linked INTEGER NOT NULL DEFAULT 0,
                    partner_occurred_at TEXT,
                    commercial_event_id TEXT,
                    crm_lead_id INTEGER,
                    lead_mapping_id INTEGER,
                    lead_status TEXT,
                    crm_linked INTEGER NOT NULL DEFAULT 0,
                    commercial_reason_code TEXT,
                    commercial_notes TEXT,
                    commercial_is_manual_override INTEGER NOT NULL DEFAULT 0,
                    commercial_occurred_at TEXT,
                    updated_at TEXT NOT NULL
                );
                """
            )

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
                payload = {
                    "company_key": item["company_key"],
                    "queue_name": item["queue_name"],
                    "priority": item["priority"],
                    "reason": item["reason"],
                    "score": item["score"],
                    "status": "pending",
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
                "dedup_decisions": self._count(conn, "dedup_decisions"),
                "review_queue": self._count(conn, "review_queue"),
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
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM canonical_companies
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._decode_company(dict(row)) for row in rows]

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

    def list_review_queue(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Return standalone review queue rows."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM review_queue
                ORDER BY priority DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_feedback_events(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """Return downstream Odoo-originated feedback events applied into standalone state."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM feedback_events
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._decode_feedback_event(dict(row)) for row in rows]

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
        return {
            **row,
            "categories": cls._decode_json(row.pop("categories_json", "[]"), []),
            "services": cls._decode_json(row.pop("services_json", "[]"), []),
            "products": cls._decode_json(row.pop("products_json", "[]"), []),
            "labels": cls._decode_json(row.pop("labels_json", "[]"), []),
            "phones": cls._decode_json(row.pop("phones_json", "[]"), []),
            "emails": cls._decode_json(row.pop("emails_json", "[]"), []),
            "contact_persons": cls._decode_json(row.pop("contact_persons_json", "[]"), []),
            "messengers": cls._decode_json(row.pop("messengers_json", "[]"), []),
            "social_links": cls._decode_json(row.pop("social_links_json", "[]"), []),
            "languages": cls._decode_json(row.pop("languages_json", "[]"), []),
            "execution_reasons": cls._decode_json(row.pop("execution_reasons_json", "[]"), []),
            "execution_flags": cls._decode_json(row.pop("execution_flags_json", "{}"), {}),
            "raw_payload": cls._decode_json(row.pop("raw_payload_json", "{}"), {}),
            "raw_evidence_refs": cls._decode_json(row.pop("raw_evidence_refs_json", "[]"), []),
        }

    @classmethod
    def _decode_company(cls, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "capabilities": cls._decode_json(row.pop("capabilities_json", "[]"), []),
            "provenance": cls._decode_json(row.pop("provenance_json", "[]"), []),
        }

    @classmethod
    def _decode_dedup_decision(cls, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "match_signals": cls._decode_json(row.pop("match_signals_json", "[]"), []),
        }

    @classmethod
    def _decode_feedback_event(cls, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "partner_linked": bool(row.get("partner_linked")),
            "crm_linked": bool(row.get("crm_linked")),
            "is_manual_override": bool(row.get("is_manual_override")),
            "payload": cls._decode_json(row.pop("payload_json", "{}"), {}),
        }

    @classmethod
    def _decode_feedback_status(cls, row: dict[str, Any]) -> FeedbackStatusProjection:
        return {
            **row,
            "routing_is_manual_override": bool(row.get("routing_is_manual_override")),
            "qualification_is_manual_override": bool(row.get("qualification_is_manual_override")),
            "partner_linked": bool(row.get("partner_linked")),
            "crm_linked": bool(row.get("crm_linked")),
            "commercial_is_manual_override": bool(row.get("commercial_is_manual_override")),
        }

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

        if event.event_type == "routing_feedback" and self._is_newer_feedback_event(payload.get("routing_occurred_at"), event.occurred_at):
            payload.update(
                {
                    "routing_event_id": event.event_id,
                    "routing_outcome": event.routing_outcome or "",
                    "manual_review_status": event.manual_review_status or "",
                    "routing_reason_code": event.reason_code or "",
                    "routing_notes": event.notes or "",
                    "routing_is_manual_override": 1 if event.is_manual_override else 0,
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
            "routing_event_id": None,
            "routing_outcome": "",
            "manual_review_status": "",
            "routing_reason_code": "",
            "routing_notes": "",
            "routing_is_manual_override": 0,
            "routing_occurred_at": None,
            "qualification_event_id": None,
            "qualification_decision_id": None,
            "qualification_status": "",
            "qualification_reason_code": "",
            "qualification_notes": "",
            "qualification_is_manual_override": 0,
            "qualification_occurred_at": None,
            "partner_linkage_event_id": None,
            "partner_id": None,
            "partner_linked": 0,
            "partner_occurred_at": None,
            "commercial_event_id": None,
            "crm_lead_id": None,
            "lead_mapping_id": None,
            "lead_status": "",
            "crm_linked": 0,
            "commercial_reason_code": "",
            "commercial_notes": "",
            "commercial_is_manual_override": 0,
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
