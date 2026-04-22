# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from magon_standalone.supplier_intelligence.deduplication_service import HybridDeduplicationService
from magon_standalone.supplier_intelligence.normalization_service import BasicEnrichmentService, BasicNormalizationService

from ..integrations.foundation import get_supplier_source_adapter
from .audit import record_audit_event
from .codes import reserve_code
from .db import utc_now
from .models import (
    Company,
    CompanyAddress,
    CompanyContact,
    SupplierCompany,
    SupplierDedupCandidate,
    SupplierMergeDecision,
    SupplierNormalizationResult,
    SupplierRatingSnapshot,
    SupplierRawIngest,
    SupplierRawRecord,
    SupplierSite,
    SupplierSourceRegistry,
    SupplierVerificationEvent,
)
from .security import AuthContext

TRUST_LEVELS = ["discovered", "normalized", "contact_confirmed", "capability_confirmed", "trusted"]
TRUST_SCORES = {
    "discovered": Decimal("0.20"),
    "normalized": Decimal("0.40"),
    "contact_confirmed": Decimal("0.60"),
    "capability_confirmed": Decimal("0.80"),
    "trusted": Decimal("1.00"),
}


@dataclass(slots=True)
class SupplierIngestSummary:
    ingest_code: str
    ingest_status: str
    source_registry_code: str
    raw_count: int
    normalized_count: int
    merged_count: int
    candidate_count: int
    replayed: bool = False


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _decimal_score(value: float | Decimal | None, fallback: str = "0.0000") -> Decimal:
    if value is None:
        return Decimal(fallback)
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.0001"))
    return Decimal(f"{float(value):.4f}")


def _capability_summary(capabilities: list[str] | None, fallback: str | None = None) -> str | None:
    items = [item for item in (capabilities or []) if item]
    if items:
        return ", ".join(items)
    return _normalize_text(fallback) or None


def _build_raw_company_payload(record: SupplierRawRecord) -> dict[str, Any]:
    raw = dict(record.raw_payload_json or {})
    raw.setdefault("source_type", record.source_type)
    raw.setdefault("source_url", record.source_url)
    raw.setdefault("external_id", record.external_id)
    raw.setdefault("company_name", record.company_name)
    raw.setdefault("address_text", record.raw_address)
    raw.setdefault("phone", record.raw_phone)
    raw.setdefault("email", record.raw_email)
    raw.setdefault("website", "")
    raw.setdefault("capabilities_text", record.raw_capability_summary or "")
    raw.setdefault("labels", [])
    raw.setdefault("categories", [])
    raw.setdefault("services", [])
    raw.setdefault("products", [])
    raw.setdefault("parser_confidence", 0.5)
    raw.setdefault("source_confidence", 0.5)
    raw.setdefault("source_fingerprint", record.source_fingerprint)
    raw.setdefault("candidate_dedup_fingerprint", record.dedup_fingerprint or "")
    raw.setdefault("raw_payload", record.raw_payload_json or {})
    raw.setdefault("normalized_at", utc_now().isoformat())
    raw.setdefault("fetched_at", record.created_at.isoformat())
    raw.setdefault("extracted_at", record.created_at.isoformat())
    raw.setdefault("discovered_at", record.created_at.isoformat())
    return raw


def _supplier_as_normalized_payload(item: SupplierCompany, address: CompanyAddress | None = None) -> dict[str, Any]:
    return {
        "canonical_key": item.code,
        "canonical_name": item.canonical_name,
        "legal_name": item.display_name,
        "brand_alias": item.display_name,
        "canonical_phone": item.canonical_phone or "",
        "canonical_email": item.canonical_email or "",
        "website": item.website or "",
        "address_text": address.normalized_address if address and address.normalized_address else address.raw_address if address else "",
        "city": address.city if address else "",
        "district": address.district if address else "",
        "country_code": address.country_code if address and address.country_code else "VN",
        "capabilities": list(item.capabilities_json or []),
        "confidence": float(item.confidence_score or 0.0),
        "parser_confidence": float(item.confidence_score or 0.0),
        "source_confidence": float(item.confidence_score or 0.0),
        "provenance": [item.code],
        "review_status": "approved",
        "source_fingerprint": item.code,
        "dedup_fingerprint": item.code,
    }


class SupplierPipelineService:
    def __init__(self, session: Session):
        self.session = session
        self.normalizer = BasicNormalizationService()
        self.enricher = BasicEnrichmentService()
        self.deduper = HybridDeduplicationService()

    def list_source_registries(self) -> list[SupplierSourceRegistry]:
        return self.session.scalars(select(SupplierSourceRegistry).order_by(SupplierSourceRegistry.created_at.asc())).all()

    def get_source_registry_by_code(self, source_code: str) -> SupplierSourceRegistry:
        item = self.session.scalar(select(SupplierSourceRegistry).where(SupplierSourceRegistry.code == source_code))
        if item is None:
            raise LookupError("supplier_source_not_found")
        return item

    def create_source_registry(
        self,
        *,
        label: str,
        adapter_key: str,
        config_json: dict | None,
        auth: AuthContext,
        reason_code: str,
    ) -> SupplierSourceRegistry:
        registry = SupplierSourceRegistry(
            code=reserve_code(self.session, "supplier_source_registries", "SRC"),
            label=label,
            adapter_key=adapter_key,
            source_layer="raw",
            enabled=True,
            config_json=config_json or {},
        )
        self.session.add(registry)
        self.session.flush()
        record_audit_event(
            self.session,
            module_name="suppliers",
            action="source_registry_created",
            entity_type="supplier_source_registry",
            entity_id=registry.id,
            entity_code=registry.code,
            auth=auth,
            reason=reason_code,
            payload_json={"adapter_key": adapter_key},
        )
        return registry

    def create_manual_supplier(
        self,
        *,
        display_name: str,
        legal_name: str | None,
        canonical_email: str | None,
        canonical_phone: str | None,
        website: str | None,
        capability_summary: str | None,
        capabilities_json: list[str] | None,
        address_text: str | None,
        city: str | None,
        district: str | None,
        country_code: str,
        auth: AuthContext,
        reason_code: str,
    ) -> SupplierCompany:
        company = Company(
            code=reserve_code(self.session, "companies", "CMP"),
            public_name=display_name,
            legal_name=legal_name,
            country_code=country_code,
            public_status="hidden",
            internal_status="supplier_registry",
            public_note="RU: Manual supplier company kept internal until trust is explicitly raised.",
            internal_note=f"Manual supplier creation via reason {reason_code}.",
        )
        self.session.add(company)
        self.session.flush()
        if canonical_email or canonical_phone:
            self.session.add(
                CompanyContact(
                    code=reserve_code(self.session, "company_contacts", "CON"),
                    company_id=company.id,
                    contact_name=display_name,
                    role_label="General",
                    email=canonical_email,
                    phone=canonical_phone,
                    is_primary=True,
                    verification_status="unverified",
                    source_note="Manual supplier admin create.",
                )
            )
        address = None
        if address_text or city:
            address = CompanyAddress(
                code=reserve_code(self.session, "company_addresses", "ADR"),
                company_id=company.id,
                label="main",
                raw_address=address_text,
                normalized_address=address_text,
                city=city,
                district=district,
                country_code=country_code,
                is_primary=True,
            )
            self.session.add(address)
            self.session.flush()
        supplier = SupplierCompany(
            code=reserve_code(self.session, "supplier_companies", "SPC"),
            company_id=company.id,
            display_name=display_name,
            canonical_name=display_name,
            supplier_status="discovered",
            trust_level="discovered",
            dedup_status="clear",
            website=website,
            canonical_email=canonical_email,
            canonical_phone=canonical_phone,
            capability_summary=_capability_summary(capabilities_json, capability_summary),
            capabilities_json=list(capabilities_json or []),
            confidence_score=Decimal("0.5000"),
        )
        self.session.add(supplier)
        self.session.flush()
        site = SupplierSite(
            code=reserve_code(self.session, "supplier_sites", "SPS"),
            supplier_company_id=supplier.id,
            address_id=address.id if address else None,
            site_name=f"{display_name} Main Site",
            site_status="active",
            trust_level="discovered",
            capability_summary=supplier.capability_summary,
            current_load_percent=0,
            lead_time_days=7,
            is_primary=True,
        )
        self.session.add(site)
        self._record_verification_event(
            supplier=supplier,
            supplier_site=site,
            verification_type="discovered",
            previous_trust_level=None,
            new_trust_level="discovered",
            auth=auth,
            reason_code=reason_code,
            note="Manual supplier admin create.",
        )
        self._create_rating_snapshot(supplier=supplier, supplier_site=site, source_label="manual_create")
        record_audit_event(
            self.session,
            module_name="suppliers",
            action="manual_create",
            entity_type="supplier_company",
            entity_id=supplier.id,
            entity_code=supplier.code,
            auth=auth,
            reason=reason_code,
            payload_json={"company_code": company.code},
        )
        return supplier

    def run_ingest(
        self,
        *,
        source_registry_code: str,
        idempotency_key: str,
        auth: AuthContext | None,
        reason_code: str,
        trigger_mode: str = "manual",
    ) -> SupplierIngestSummary:
        registry = self.get_source_registry_by_code(source_registry_code)
        existing = self.session.scalar(
            select(SupplierRawIngest).where(SupplierRawIngest.idempotency_key == idempotency_key)
        )
        if existing is not None:
            if existing.ingest_status == "completed":
                return SupplierIngestSummary(
                    ingest_code=existing.code,
                    ingest_status=existing.ingest_status,
                    source_registry_code=registry.code,
                    raw_count=existing.raw_count,
                    normalized_count=existing.normalized_count,
                    merged_count=existing.merged_count,
                    candidate_count=existing.candidate_count,
                    replayed=True,
                )
            if existing.ingest_status == "running":
                return SupplierIngestSummary(
                    ingest_code=existing.code,
                    ingest_status=existing.ingest_status,
                    source_registry_code=registry.code,
                    raw_count=existing.raw_count,
                    normalized_count=existing.normalized_count,
                    merged_count=existing.merged_count,
                    candidate_count=existing.candidate_count,
                    replayed=True,
                )
            previous_status = existing.ingest_status
            ingest = existing
            ingest.ingest_status = "running"
            ingest.started_at = utc_now()
            ingest.finished_at = None
            ingest.failed_at = None
            ingest.failure_code = None
            ingest.failure_detail = None
            ingest.raw_count = 0
            ingest.normalized_count = 0
            ingest.merged_count = 0
            ingest.candidate_count = 0
            if previous_status == "failed":
                ingest.last_retry_at = utc_now()
                ingest.retry_count = int(ingest.retry_count or 0) + 1
            # RU: И queued job, и retry используют тот же ingest row, чтобы async/operator история оставалась связной и explainable.
            self._cleanup_ingest_rows(ingest=ingest)
            self.session.flush()
        else:
            ingest = SupplierRawIngest(
                code=reserve_code(self.session, "supplier_raw_ingests", "ING"),
                source_registry_id=registry.id,
                idempotency_key=idempotency_key,
                ingest_status="running",
                reason_code=reason_code,
                trigger_mode=trigger_mode,
                adapter_key=registry.adapter_key,
                started_at=utc_now(),
                requested_by_user_id=auth.user_id if auth else None,
            )
            self.session.add(ingest)
            self.session.flush()

        try:
            adapter = get_supplier_source_adapter(registry.adapter_key)
            pulled = adapter.pull(registry.config_json or {})
            raw_records = self._store_raw_records(registry, ingest, pulled.records)
            normalization_results = self._normalize_raw_records(ingest, raw_records)

            merged_count = 0
            candidate_count = 0
            for item in normalization_results:
                outcome = self._promote_normalized_result(item, registry, ingest, auth)
                if outcome == "merged":
                    merged_count += 1
                if outcome == "candidate":
                    candidate_count += 1

            ingest.ingest_status = "completed"
            ingest.finished_at = utc_now()
            ingest.raw_count = len(raw_records)
            ingest.normalized_count = len(normalization_results)
            ingest.merged_count = merged_count
            ingest.candidate_count = candidate_count
            registry.last_success_at = ingest.finished_at

            record_audit_event(
                self.session,
                module_name="suppliers",
                action="ingest_completed",
                entity_type="supplier_ingest",
                entity_id=ingest.id,
                entity_code=ingest.code,
                auth=auth,
                reason=reason_code,
                payload_json={
                    "source_registry_code": registry.code,
                    "raw_count": ingest.raw_count,
                    "normalized_count": ingest.normalized_count,
                    "merged_count": ingest.merged_count,
                    "candidate_count": ingest.candidate_count,
                    "retry_count": ingest.retry_count,
                },
            )
            return SupplierIngestSummary(
                ingest_code=ingest.code,
                ingest_status=ingest.ingest_status,
                source_registry_code=registry.code,
                raw_count=ingest.raw_count,
                normalized_count=ingest.normalized_count,
                merged_count=ingest.merged_count,
                candidate_count=ingest.candidate_count,
                replayed=False,
            )
        except Exception as exc:
            ingest.ingest_status = "failed"
            ingest.failed_at = utc_now()
            ingest.finished_at = ingest.failed_at
            ingest.failure_code = exc.__class__.__name__
            ingest.failure_detail = str(exc)[:2000]
            record_audit_event(
                self.session,
                module_name="suppliers",
                action="ingest_failed",
                entity_type="supplier_ingest",
                entity_id=ingest.id,
                entity_code=ingest.code,
                auth=auth,
                reason=reason_code,
                payload_json={
                    "source_registry_code": registry.code,
                    "failure_code": ingest.failure_code,
                    "failure_detail": ingest.failure_detail,
                    "retry_count": ingest.retry_count,
                },
            )
            return SupplierIngestSummary(
                ingest_code=ingest.code,
                ingest_status=ingest.ingest_status,
                source_registry_code=registry.code,
                raw_count=ingest.raw_count,
                normalized_count=ingest.normalized_count,
                merged_count=ingest.merged_count,
                candidate_count=ingest.candidate_count,
                replayed=False,
            )

    def retry_ingest(
        self,
        *,
        ingest_code: str,
        auth: AuthContext | None,
        reason_code: str,
        trigger_mode: str = "manual",
    ) -> SupplierIngestSummary:
        ingest = self.session.scalar(select(SupplierRawIngest).where(SupplierRawIngest.code == ingest_code))
        if ingest is None:
            raise LookupError("supplier_ingest_not_found")
        if ingest.ingest_status != "failed":
            raise ValueError("supplier_ingest_retry_not_allowed")
        registry = self.session.get(SupplierSourceRegistry, ingest.source_registry_id)
        if registry is None:
            raise LookupError("supplier_source_not_found")
        return self.run_ingest(
            source_registry_code=registry.code,
            idempotency_key=ingest.idempotency_key,
            auth=auth,
            reason_code=reason_code,
            trigger_mode=trigger_mode,
        )

    def _cleanup_ingest_rows(self, *, ingest: SupplierRawIngest) -> None:
        normalization_ids = list(
            self.session.scalars(select(SupplierNormalizationResult.id).where(SupplierNormalizationResult.ingest_id == ingest.id)).all()
        )
        if normalization_ids:
            for candidate in self.session.scalars(
                select(SupplierDedupCandidate).where(SupplierDedupCandidate.ingest_id == ingest.id)
            ).all():
                self.session.delete(candidate)
            for item in self.session.scalars(
                select(SupplierNormalizationResult).where(SupplierNormalizationResult.id.in_(normalization_ids))
            ).all():
                self.session.delete(item)
        for raw in self.session.scalars(select(SupplierRawRecord).where(SupplierRawRecord.ingest_id == ingest.id)).all():
            self.session.delete(raw)

    def apply_trust_transition(
        self,
        *,
        supplier_code: str,
        target_trust_level: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> SupplierCompany:
        supplier = self._get_supplier_by_code(supplier_code)
        if target_trust_level not in TRUST_LEVELS:
            raise ValueError("invalid_trust_level")
        previous = supplier.trust_level
        current_index = TRUST_LEVELS.index(previous)
        target_index = TRUST_LEVELS.index(target_trust_level)
        if target_index <= current_index:
            raise ValueError("trust_level_not_forward")
        if target_index - current_index != 1:
            raise ValueError("trust_level_skip_forbidden")
        if target_trust_level == "contact_confirmed" and not (supplier.canonical_email or supplier.canonical_phone):
            raise ValueError("contact_confirmation_requires_contact")
        if target_trust_level == "capability_confirmed" and not (supplier.capability_summary or supplier.capabilities_json):
            raise ValueError("capability_confirmation_requires_capabilities")
        if target_trust_level == "trusted" and (supplier.contact_confirmed_at is None or supplier.capability_confirmed_at is None):
            raise ValueError("trusted_requires_contact_and_capability")

        supplier.trust_level = target_trust_level
        now = utc_now()
        if target_trust_level == "contact_confirmed":
            supplier.contact_confirmed_at = now
        if target_trust_level == "capability_confirmed":
            supplier.capability_confirmed_at = now
        if target_trust_level == "trusted":
            supplier.trusted_at = now
            supplier.supplier_status = "active"

        self._record_verification_event(
            supplier=supplier,
            supplier_site=None,
            verification_type=target_trust_level,
            previous_trust_level=previous,
            new_trust_level=target_trust_level,
            auth=auth,
            reason_code=reason_code,
            note=note,
        )
        self._create_rating_snapshot(supplier=supplier, supplier_site=None, source_label="manual_verification")
        record_audit_event(
            self.session,
            module_name="suppliers",
            action="trust_transition",
            entity_type="supplier_company",
            entity_id=supplier.id,
            entity_code=supplier.code,
            auth=auth,
            reason=reason_code,
            payload_json={"from": previous, "to": target_trust_level, "note": note},
        )
        return supplier

    def block_supplier(self, *, supplier_code: str, auth: AuthContext, reason_code: str, note: str | None = None) -> SupplierCompany:
        supplier = self._get_supplier_by_code(supplier_code)
        supplier.supplier_status = "blocked"
        supplier.blocked_at = utc_now()
        supplier.blocked_reason = reason_code
        self._record_verification_event(
            supplier=supplier,
            supplier_site=None,
            verification_type="blocked",
            previous_trust_level=supplier.trust_level,
            new_trust_level=supplier.trust_level,
            auth=auth,
            reason_code=reason_code,
            note=note,
        )
        record_audit_event(
            self.session,
            module_name="suppliers",
            action="blocked",
            entity_type="supplier_company",
            entity_id=supplier.id,
            entity_code=supplier.code,
            auth=auth,
            reason=reason_code,
            payload_json={"note": note},
        )
        return supplier

    def archive_supplier(self, *, supplier_code: str, auth: AuthContext, reason_code: str, note: str | None = None) -> SupplierCompany:
        supplier = self._get_supplier_by_code(supplier_code)
        supplier.archived_at = utc_now()
        supplier.archived_reason = reason_code
        supplier.supplier_status = "archived"
        record_audit_event(
            self.session,
            module_name="suppliers",
            action="archived",
            entity_type="supplier_company",
            entity_id=supplier.id,
            entity_code=supplier.code,
            auth=auth,
            reason=reason_code,
            payload_json={"note": note},
        )
        return supplier

    def resolve_dedup_candidate(
        self,
        *,
        candidate_code: str,
        decision: str,
        auth: AuthContext,
        reason_code: str,
        note: str | None = None,
    ) -> SupplierDedupCandidate:
        candidate = self.session.scalar(select(SupplierDedupCandidate).where(SupplierDedupCandidate.code == candidate_code))
        if candidate is None:
            raise LookupError("dedup_candidate_not_found")
        if candidate.candidate_status != "pending_review":
            raise ValueError("dedup_candidate_already_resolved")

        normalization = self.session.get(SupplierNormalizationResult, candidate.normalization_result_id)
        matched_supplier = self.session.get(SupplierCompany, candidate.matched_supplier_company_id)
        if normalization is None or matched_supplier is None:
            raise LookupError("dedup_candidate_broken_link")

        if decision == "merge":
            self._merge_into_existing_supplier(
                supplier=matched_supplier,
                normalization=normalization,
                raw_record=self.session.get(SupplierRawRecord, normalization.raw_record_id),
                reason_code=reason_code,
            )
            candidate.candidate_status = "merged"
            decision_status = "merged"
            decision_supplier_id = matched_supplier.id
        elif decision == "reject":
            created_supplier = self._create_confirmed_supplier_from_normalized(normalization=normalization, registry=None)
            candidate.candidate_status = "rejected_as_duplicate"
            decision_status = "rejected"
            decision_supplier_id = created_supplier.id
        else:
            raise ValueError("invalid_dedup_decision")

        merge_decision = SupplierMergeDecision(
            code=reserve_code(self.session, "supplier_merge_decisions", "MRG"),
            dedup_candidate_id=candidate.id,
            normalization_result_id=normalization.id,
            supplier_company_id=decision_supplier_id,
            decision_status=decision_status,
            reason_code=reason_code,
            notes=note,
            decided_by_user_id=auth.user_id,
            decided_at=utc_now(),
        )
        self.session.add(merge_decision)
        record_audit_event(
            self.session,
            module_name="suppliers",
            action="dedup_resolved",
            entity_type="supplier_dedup_candidate",
            entity_id=candidate.id,
            entity_code=candidate.code,
            auth=auth,
            reason=reason_code,
            payload_json={"decision": decision, "note": note},
        )
        return candidate

    def _store_raw_records(
        self,
        registry: SupplierSourceRegistry,
        ingest: SupplierRawIngest,
        records: list[dict[str, Any]],
    ) -> list[SupplierRawRecord]:
        stored: list[SupplierRawRecord] = []
        for payload in records:
            source_fingerprint = str(payload.get("source_fingerprint") or payload.get("external_id") or reserve_code(self.session, "supplier_raw_fallback", "RAW"))
            item = self.session.scalar(
                select(SupplierRawRecord).where(
                    SupplierRawRecord.ingest_id == ingest.id,
                    SupplierRawRecord.source_fingerprint == source_fingerprint,
                )
            )
            if item is None:
                item = SupplierRawRecord(
                    code=reserve_code(self.session, "supplier_raw_records", "RAW"),
                    source_registry_id=registry.id,
                    ingest_id=ingest.id,
                    source_type=str(payload.get("source_type") or "directory"),
                    source_url=str(payload.get("source_url") or ""),
                    external_id=str(payload.get("external_id") or "") or None,
                    company_name=str(payload.get("company_name") or ""),
                    raw_email=_normalize_text(payload.get("email")),
                    raw_phone=_normalize_text(payload.get("phone")),
                    raw_address=_normalize_text(payload.get("address_text")),
                    raw_capability_summary=_normalize_text(payload.get("capabilities_text")),
                    source_fingerprint=source_fingerprint,
                    dedup_fingerprint=_normalize_text(payload.get("candidate_dedup_fingerprint")) or None,
                    raw_payload_json=payload,
                )
                self.session.add(item)
                self.session.flush()
            stored.append(item)
        return stored

    def _normalize_raw_records(
        self,
        ingest: SupplierRawIngest,
        raw_records: list[SupplierRawRecord],
    ) -> list[SupplierNormalizationResult]:
        normalized_inputs = [_build_raw_company_payload(item) for item in raw_records]
        normalized_rows = self.enricher.enrich(self.normalizer.normalize(normalized_inputs))
        results: list[SupplierNormalizationResult] = []
        for raw_record, row in zip(raw_records, normalized_rows, strict=False):
            result = self.session.scalar(
                select(SupplierNormalizationResult).where(
                    SupplierNormalizationResult.ingest_id == ingest.id,
                    SupplierNormalizationResult.raw_record_id == raw_record.id,
                )
            )
            if result is None:
                result = SupplierNormalizationResult(
                    code=reserve_code(self.session, "supplier_normalization_results", "NOR"),
                    ingest_id=ingest.id,
                    raw_record_id=raw_record.id,
                    normalized_status="normalized",
                    canonical_key=str(row.get("canonical_key") or raw_record.code),
                    canonical_name=str(row.get("canonical_name") or raw_record.company_name),
                    legal_name=_normalize_text(row.get("legal_name")) or None,
                    canonical_email=_normalize_text(row.get("canonical_email")) or None,
                    canonical_phone=_normalize_text(row.get("canonical_phone")) or None,
                    website=_normalize_text(row.get("website")) or None,
                    address_text=_normalize_text(row.get("address_text")) or None,
                    city=_normalize_text(row.get("city")) or None,
                    district=_normalize_text(row.get("district")) or None,
                    country_code=str(row.get("country_code") or "VN"),
                    capability_summary=_capability_summary(row.get("capabilities"), raw_record.raw_capability_summary),
                    capabilities_json=list(row.get("capabilities") or []),
                    confidence_score=_decimal_score(row.get("confidence")),
                    dedup_fingerprint=_normalize_text(row.get("dedup_fingerprint")) or raw_record.dedup_fingerprint,
                    normalization_payload_json=row,
                )
                self.session.add(result)
                self.session.flush()
            results.append(result)
        return results

    def _promote_normalized_result(
        self,
        normalization: SupplierNormalizationResult,
        registry: SupplierSourceRegistry,
        ingest: SupplierRawIngest,
        auth: AuthContext | None,
    ) -> str:
        raw_record = self.session.get(SupplierRawRecord, normalization.raw_record_id)
        if raw_record is None:
            raise LookupError("raw_record_not_found")
        match = self._best_match_for_normalized(normalization)
        if match is None:
            self._create_confirmed_supplier_from_normalized(normalization=normalization, registry=registry)
            return "created"
        decision, confidence, signals, supplier = match
        if decision == "same_entity":
            self._merge_into_existing_supplier(
                supplier=supplier,
                normalization=normalization,
                raw_record=raw_record,
                reason_code="dedup_auto_match",
            )
            merge_decision = SupplierMergeDecision(
                code=reserve_code(self.session, "supplier_merge_decisions", "MRG"),
                normalization_result_id=normalization.id,
                supplier_company_id=supplier.id,
                decision_status="auto_merged",
                reason_code="dedup_auto_match",
                notes="Automatic same-entity merge during ingest.",
            )
            self.session.add(merge_decision)
            record_audit_event(
                self.session,
                module_name="suppliers",
                action="auto_merged",
                entity_type="supplier_company",
                entity_id=supplier.id,
                entity_code=supplier.code,
                auth=auth,
                reason="dedup_auto_match",
                payload_json={"normalization_code": normalization.code, "confidence": float(confidence)},
            )
            return "merged"

        candidate = SupplierDedupCandidate(
            code=reserve_code(self.session, "supplier_dedup_candidates", "DDC"),
            ingest_id=ingest.id,
            normalization_result_id=normalization.id,
            matched_supplier_company_id=supplier.id,
            candidate_status="pending_review",
            suggested_decision="merge",
            confidence_score=_decimal_score(confidence),
            reason_code="dedup_manual_review",
            signals_json=signals,
        )
        self.session.add(candidate)
        self.session.flush()
        normalization.normalized_status = "needs_manual_review"
        record_audit_event(
            self.session,
            module_name="suppliers",
            action="dedup_candidate_created",
            entity_type="supplier_dedup_candidate",
            entity_id=candidate.id,
            entity_code=candidate.code,
            auth=auth,
            reason="dedup_manual_review",
            payload_json={"supplier_code": supplier.code, "normalization_code": normalization.code},
        )
        return "candidate"

    def _best_match_for_normalized(
        self,
        normalization: SupplierNormalizationResult,
    ) -> tuple[str, float, dict[str, Any], SupplierCompany] | None:
        address_map = {
            item.id: item
            for item in self.session.scalars(select(CompanyAddress).where(CompanyAddress.deleted_at.is_(None))).all()
        }
        normalized_payload = {
            "canonical_key": normalization.canonical_key,
            "canonical_name": normalization.canonical_name,
            "brand_alias": normalization.legal_name or normalization.canonical_name,
            "canonical_phone": normalization.canonical_phone or "",
            "canonical_email": normalization.canonical_email or "",
            "website": normalization.website or "",
            "address_text": normalization.address_text or "",
            "city": normalization.city or "",
            "district": normalization.district or "",
            "country_code": normalization.country_code,
            "capabilities": list(normalization.capabilities_json or []),
            "confidence": float(normalization.confidence_score or 0.0),
            "parser_confidence": float(normalization.confidence_score or 0.0),
            "source_confidence": float(normalization.confidence_score or 0.0),
            "provenance": [normalization.code],
            "review_status": "new",
            "source_fingerprint": normalization.code,
            "dedup_fingerprint": normalization.dedup_fingerprint or normalization.code,
        }
        best: tuple[str, float, dict[str, Any], SupplierCompany] | None = None
        suppliers = self.session.scalars(
            select(SupplierCompany).where(SupplierCompany.deleted_at.is_(None)).order_by(SupplierCompany.created_at.asc())
        ).all()
        for supplier in suppliers:
            address = self.session.scalar(
                select(CompanyAddress)
                .where(CompanyAddress.company_id == supplier.company_id, CompanyAddress.deleted_at.is_(None))
                .order_by(CompanyAddress.created_at.asc())
            )
            candidate_payload = _supplier_as_normalized_payload(supplier, address)
            signals = self.deduper._match_signals(normalized_payload, candidate_payload)  # type: ignore[attr-defined]
            decision, confidence = self.deduper._classify(signals)  # type: ignore[attr-defined]
            if decision == "different_entity":
                continue
            if best is None or confidence > best[1]:
                best = (decision, confidence, signals, supplier)
        return best

    def _create_confirmed_supplier_from_normalized(
        self,
        *,
        normalization: SupplierNormalizationResult,
        registry: SupplierSourceRegistry | None,
    ) -> SupplierCompany:
        company = Company(
            code=reserve_code(self.session, "companies", "CMP"),
            public_name=normalization.canonical_name,
            legal_name=normalization.legal_name,
            country_code=normalization.country_code,
            public_status="hidden",
            internal_status="supplier_registry",
            public_note="RU: Confirmed supplier company created from normalized supplier ingest.",
            internal_note=f"Created from normalization result {normalization.code}.",
        )
        self.session.add(company)
        self.session.flush()

        if normalization.canonical_email or normalization.canonical_phone:
            self.session.add(
                CompanyContact(
                    code=reserve_code(self.session, "company_contacts", "CON"),
                    company_id=company.id,
                    contact_name=normalization.canonical_name,
                    role_label="General",
                    email=normalization.canonical_email,
                    phone=normalization.canonical_phone,
                    is_primary=True,
                    verification_status="discovered",
                    source_note=f"Imported from normalization result {normalization.code}.",
                )
            )

        address = None
        if normalization.address_text or normalization.city:
            address = CompanyAddress(
                code=reserve_code(self.session, "company_addresses", "ADR"),
                company_id=company.id,
                label="main",
                raw_address=normalization.address_text,
                normalized_address=normalization.address_text,
                city=normalization.city,
                district=normalization.district,
                country_code=normalization.country_code,
                is_primary=True,
            )
            self.session.add(address)
            self.session.flush()

        supplier = SupplierCompany(
            code=reserve_code(self.session, "supplier_companies", "SPC"),
            company_id=company.id,
            source_registry_id=registry.id if registry else None,
            display_name=normalization.canonical_name,
            canonical_name=normalization.canonical_name,
            supplier_status="normalized",
            trust_level="normalized",
            dedup_status="clear",
            website=normalization.website,
            canonical_email=normalization.canonical_email,
            canonical_phone=normalization.canonical_phone,
            capability_summary=normalization.capability_summary,
            capabilities_json=list(normalization.capabilities_json or []),
            confidence_score=normalization.confidence_score,
        )
        self.session.add(supplier)
        self.session.flush()
        normalization.supplier_company_id = supplier.id
        normalization.normalized_status = "confirmed"

        self.session.add(
            SupplierSite(
                code=reserve_code(self.session, "supplier_sites", "SPS"),
                supplier_company_id=supplier.id,
                address_id=address.id if address else None,
                site_name=f"{supplier.display_name} Main Site",
                site_status="active",
                trust_level="normalized",
                capability_summary=supplier.capability_summary,
                current_load_percent=0,
                lead_time_days=7,
                is_primary=True,
            )
        )
        self.session.flush()
        self._record_verification_event(
            supplier=supplier,
            supplier_site=None,
            verification_type="normalized",
            previous_trust_level="discovered",
            new_trust_level="normalized",
            auth=None,
            reason_code="ingest_normalized",
            note="Automatic promotion from normalized supplier import.",
        )
        self._create_rating_snapshot(supplier=supplier, supplier_site=None, source_label="normalized_ingest")
        return supplier

    def _merge_into_existing_supplier(
        self,
        *,
        supplier: SupplierCompany,
        normalization: SupplierNormalizationResult,
        raw_record: SupplierRawRecord | None,
        reason_code: str,
    ) -> None:
        company = self.session.get(Company, supplier.company_id)
        if company is None:
            raise LookupError("supplier_company_missing_company")
        if not supplier.website and normalization.website:
            supplier.website = normalization.website
        if not supplier.canonical_email and normalization.canonical_email:
            supplier.canonical_email = normalization.canonical_email
        if not supplier.canonical_phone and normalization.canonical_phone:
            supplier.canonical_phone = normalization.canonical_phone
        merged_capabilities = list(dict.fromkeys(list(supplier.capabilities_json or []) + list(normalization.capabilities_json or [])))
        supplier.capabilities_json = merged_capabilities
        supplier.capability_summary = _capability_summary(merged_capabilities, supplier.capability_summary or normalization.capability_summary)
        supplier.confidence_score = max(
            _decimal_score(supplier.confidence_score),
            _decimal_score(normalization.confidence_score),
        )
        supplier.trust_level = "normalized"
        normalization.supplier_company_id = supplier.id
        normalization.normalized_status = "merged_into_confirmed"

        contact = self.session.scalar(
            select(CompanyContact).where(CompanyContact.company_id == company.id, CompanyContact.deleted_at.is_(None)).order_by(CompanyContact.created_at.asc())
        )
        if contact is None and (normalization.canonical_email or normalization.canonical_phone):
            self.session.add(
                CompanyContact(
                    code=reserve_code(self.session, "company_contacts", "CON"),
                    company_id=company.id,
                    contact_name=supplier.display_name,
                    role_label="General",
                    email=normalization.canonical_email,
                    phone=normalization.canonical_phone,
                    is_primary=True,
                    verification_status="discovered",
                    source_note=f"Merged from normalization {normalization.code}.",
                )
            )

        address = self.session.scalar(
            select(CompanyAddress).where(CompanyAddress.company_id == company.id, CompanyAddress.deleted_at.is_(None)).order_by(CompanyAddress.created_at.asc())
        )
        if address is None and (normalization.address_text or normalization.city):
            address = CompanyAddress(
                code=reserve_code(self.session, "company_addresses", "ADR"),
                company_id=company.id,
                label="main",
                raw_address=normalization.address_text,
                normalized_address=normalization.address_text,
                city=normalization.city,
                district=normalization.district,
                country_code=normalization.country_code,
                is_primary=True,
            )
            self.session.add(address)
            self.session.flush()

        site = self.session.scalar(
            select(SupplierSite)
            .where(SupplierSite.supplier_company_id == supplier.id, SupplierSite.deleted_at.is_(None))
            .order_by(SupplierSite.created_at.asc())
        )
        if site is None:
            site = SupplierSite(
                code=reserve_code(self.session, "supplier_sites", "SPS"),
                supplier_company_id=supplier.id,
                address_id=address.id if address else None,
                site_name=f"{supplier.display_name} Main Site",
                site_status="active",
                trust_level=supplier.trust_level,
                capability_summary=supplier.capability_summary,
                current_load_percent=0,
                lead_time_days=7,
                is_primary=True,
            )
            self.session.add(site)
        else:
            if site.address_id is None and address is not None:
                site.address_id = address.id
            if not site.capability_summary and supplier.capability_summary:
                site.capability_summary = supplier.capability_summary
        self.session.flush()
        self._create_rating_snapshot(supplier=supplier, supplier_site=site, source_label=reason_code)
        if raw_record is not None and raw_record.dedup_fingerprint:
            supplier.dedup_status = "merged"

    def _record_verification_event(
        self,
        *,
        supplier: SupplierCompany,
        supplier_site: SupplierSite | None,
        verification_type: str,
        previous_trust_level: str | None,
        new_trust_level: str | None,
        auth: AuthContext | None,
        reason_code: str,
        note: str | None,
    ) -> None:
        self.session.add(
            SupplierVerificationEvent(
                code=reserve_code(self.session, "supplier_verification_events", "VER"),
                supplier_company_id=supplier.id,
                supplier_site_id=supplier_site.id if supplier_site else None,
                verification_type=verification_type,
                previous_trust_level=previous_trust_level,
                new_trust_level=new_trust_level,
                reason_code=reason_code,
                note=note,
                verified_by_user_id=auth.user_id if auth else None,
            )
        )

    def _create_rating_snapshot(
        self,
        *,
        supplier: SupplierCompany,
        supplier_site: SupplierSite | None,
        source_label: str,
    ) -> None:
        load_percent = supplier_site.current_load_percent if supplier_site and supplier_site.current_load_percent is not None else 0
        load_score = Decimal("1.0000") - (Decimal(load_percent) / Decimal("100"))
        trust_score = TRUST_SCORES.get(supplier.trust_level, Decimal("0.2000"))
        quality_score = max(_decimal_score(supplier.confidence_score, "0.4000"), Decimal("0.4000"))
        overall_score = ((quality_score + trust_score + load_score) / Decimal("3")).quantize(Decimal("0.0001"))
        self.session.add(
            SupplierRatingSnapshot(
                code=reserve_code(self.session, "supplier_rating_snapshots", "RAT"),
                supplier_company_id=supplier.id,
                supplier_site_id=supplier_site.id if supplier_site else None,
                quality_score=quality_score,
                trust_score=trust_score,
                load_score=load_score.quantize(Decimal("0.0001")),
                overall_score=overall_score,
                current_load_percent=load_percent,
                source_label=source_label,
            )
        )

    def _get_supplier_by_code(self, supplier_code: str) -> SupplierCompany:
        supplier = self.session.scalar(select(SupplierCompany).where(SupplierCompany.code == supplier_code))
        if supplier is None:
            raise LookupError("supplier_not_found")
        return supplier
