# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles
from ..models import (
    Company,
    CompanyAddress,
    CompanyContact,
    SupplierCompany,
    SupplierDedupCandidate,
    SupplierNormalizationResult,
    SupplierRatingSnapshot,
    SupplierRawIngest,
    SupplierRawRecord,
    SupplierSite,
    SupplierSourceRegistry,
    SupplierVerificationEvent,
)
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from ..supplier_services import SupplierPipelineService, SupplierIngestSummary
from ..celery_app import run_supplier_ingest
from .shared import (
    company_address_view,
    company_contact_view,
    company_operator_view,
    iso_or_none,
    supplier_operator_view,
    supplier_public_view,
    supplier_site_view,
)

router = APIRouter(tags=["Suppliers"])


class SupplierSourceCreatePayload(BaseModel):
    label: str = Field(min_length=3)
    adapter_key: str = Field(min_length=3)
    config_json: dict | None = None
    reason_code: str = "admin_create_supplier_source"


class SupplierIngestPayload(BaseModel):
    source_registry_code: str
    idempotency_key: str = Field(min_length=3)
    reason_code: str = "manual_supplier_ingest"


class SupplierCreatePayload(BaseModel):
    display_name: str = Field(min_length=2)
    legal_name: str | None = None
    canonical_email: str | None = None
    canonical_phone: str | None = None
    website: str | None = None
    capability_summary: str | None = None
    capabilities_json: list[str] = Field(default_factory=list)
    address_text: str | None = None
    city: str | None = None
    district: str | None = None
    country_code: str = "VN"
    reason_code: str = "admin_create_supplier"


class SupplierVerifyPayload(BaseModel):
    target_trust_level: Literal["normalized", "contact_confirmed", "capability_confirmed", "trusted"]
    reason_code: str
    note: str | None = None


class SupplierStatusPayload(BaseModel):
    reason_code: str
    note: str | None = None


class SupplierDedupDecisionPayload(BaseModel):
    decision: Literal["merge", "reject"]
    reason_code: str
    note: str | None = None


def _service(session: Session) -> SupplierPipelineService:
    return SupplierPipelineService(session)


def _ingest_view(item: SupplierRawIngest, registry: SupplierSourceRegistry | None = None) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "source_registry_id": item.source_registry_id,
        "source_registry_code": registry.code if registry else None,
        "ingest_status": item.ingest_status,
        "idempotency_key": item.idempotency_key,
        "reason_code": item.reason_code,
        "task_id": item.task_id,
        "trigger_mode": item.trigger_mode,
        "adapter_key": item.adapter_key,
        "raw_count": item.raw_count,
        "normalized_count": item.normalized_count,
        "merged_count": item.merged_count,
        "candidate_count": item.candidate_count,
        "started_at": iso_or_none(item.started_at),
        "finished_at": iso_or_none(item.finished_at),
        "created_at": iso_or_none(item.created_at),
    }


def _source_registry_view(item: SupplierSourceRegistry) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "label": item.label,
        "adapter_key": item.adapter_key,
        "source_layer": item.source_layer,
        "enabled": item.enabled,
        "config_json": item.config_json or {},
        "last_success_at": iso_or_none(item.last_success_at),
        "created_at": iso_or_none(item.created_at),
    }


def _raw_record_view(item: SupplierRawRecord, normalization: SupplierNormalizationResult | None = None) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "ingest_id": item.ingest_id,
        "source_type": item.source_type,
        "source_url": item.source_url,
        "external_id": item.external_id,
        "raw_status": item.raw_status,
        "company_name": item.company_name,
        "raw_email": item.raw_email,
        "raw_phone": item.raw_phone,
        "raw_address": item.raw_address,
        "raw_capability_summary": item.raw_capability_summary,
        "source_fingerprint": item.source_fingerprint,
        "dedup_fingerprint": item.dedup_fingerprint,
        "raw_payload_json": item.raw_payload_json,
        "normalization": _normalization_view(normalization) if normalization else None,
        "created_at": iso_or_none(item.created_at),
    }


def _normalization_view(item: SupplierNormalizationResult) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "ingest_id": item.ingest_id,
        "raw_record_id": item.raw_record_id,
        "normalized_status": item.normalized_status,
        "canonical_key": item.canonical_key,
        "canonical_name": item.canonical_name,
        "legal_name": item.legal_name,
        "canonical_email": item.canonical_email,
        "canonical_phone": item.canonical_phone,
        "website": item.website,
        "address_text": item.address_text,
        "city": item.city,
        "district": item.district,
        "country_code": item.country_code,
        "capability_summary": item.capability_summary,
        "capabilities_json": list(item.capabilities_json or []),
        "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
        "supplier_company_id": item.supplier_company_id,
        "dedup_fingerprint": item.dedup_fingerprint,
        "created_at": iso_or_none(item.created_at),
    }


def _candidate_view(item: SupplierDedupCandidate, normalization: SupplierNormalizationResult | None = None, supplier: SupplierCompany | None = None) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "ingest_id": item.ingest_id,
        "normalization_result_id": item.normalization_result_id,
        "matched_supplier_company_id": item.matched_supplier_company_id,
        "candidate_status": item.candidate_status,
        "suggested_decision": item.suggested_decision,
        "confidence_score": float(item.confidence_score),
        "reason_code": item.reason_code,
        "signals_json": item.signals_json or {},
        "normalization": _normalization_view(normalization) if normalization else None,
        "matched_supplier": supplier_operator_view(supplier) if supplier else None,
        "created_at": iso_or_none(item.created_at),
    }


def _verification_view(item: SupplierVerificationEvent) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "supplier_company_id": item.supplier_company_id,
        "supplier_site_id": item.supplier_site_id,
        "verification_type": item.verification_type,
        "previous_trust_level": item.previous_trust_level,
        "new_trust_level": item.new_trust_level,
        "reason_code": item.reason_code,
        "note": item.note,
        "verified_by_user_id": item.verified_by_user_id,
        "occurred_at": iso_or_none(item.occurred_at),
        "created_at": iso_or_none(item.created_at),
    }


def _rating_view(item: SupplierRatingSnapshot) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "supplier_company_id": item.supplier_company_id,
        "supplier_site_id": item.supplier_site_id,
        "quality_score": float(item.quality_score),
        "trust_score": float(item.trust_score),
        "load_score": float(item.load_score),
        "overall_score": float(item.overall_score),
        "current_load_percent": item.current_load_percent,
        "source_label": item.source_label,
        "captured_at": iso_or_none(item.captured_at),
    }


def _supplier_detail_view(session: Session, supplier: SupplierCompany) -> dict[str, object]:
    company = session.get(Company, supplier.company_id)
    contacts = session.scalars(
        select(CompanyContact).where(CompanyContact.company_id == supplier.company_id, CompanyContact.deleted_at.is_(None)).order_by(CompanyContact.created_at.asc())
    ).all()
    addresses = session.scalars(
        select(CompanyAddress).where(CompanyAddress.company_id == supplier.company_id, CompanyAddress.deleted_at.is_(None)).order_by(CompanyAddress.created_at.asc())
    ).all()
    sites = session.scalars(
        select(SupplierSite).where(SupplierSite.supplier_company_id == supplier.id, SupplierSite.deleted_at.is_(None)).order_by(SupplierSite.created_at.asc())
    ).all()
    verifications = session.scalars(
        select(SupplierVerificationEvent).where(SupplierVerificationEvent.supplier_company_id == supplier.id).order_by(SupplierVerificationEvent.occurred_at.desc())
    ).all()
    ratings = session.scalars(
        select(SupplierRatingSnapshot).where(SupplierRatingSnapshot.supplier_company_id == supplier.id).order_by(SupplierRatingSnapshot.captured_at.desc())
    ).all()
    normalizations = session.scalars(
        select(SupplierNormalizationResult).where(SupplierNormalizationResult.supplier_company_id == supplier.id).order_by(SupplierNormalizationResult.created_at.desc())
    ).all()
    raw_records: list[SupplierRawRecord] = []
    for item in normalizations:
        raw = session.get(SupplierRawRecord, item.raw_record_id)
        if raw is not None:
            raw_records.append(raw)
    return {
        "supplier": supplier_operator_view(supplier),
        "company": company_operator_view(company) if company else None,
        "contacts": [company_contact_view(item) for item in contacts],
        "addresses": [company_address_view(item) for item in addresses],
        "sites": [supplier_site_view(item) for item in sites],
        "verification_history": [_verification_view(item) for item in verifications],
        "rating_history": [_rating_view(item) for item in ratings],
        "normalized_records": [_normalization_view(item) for item in normalizations],
        "raw_records": [_raw_record_view(item) for item in raw_records],
    }


@router.get("/api/v1/public/suppliers")
def public_suppliers(session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(
        select(SupplierCompany)
        .where(
            SupplierCompany.deleted_at.is_(None),
            SupplierCompany.archived_at.is_(None),
            SupplierCompany.supplier_status != "blocked",
            SupplierCompany.trust_level == "trusted",
        )
        .order_by(SupplierCompany.created_at.asc())
    ).all()
    return {"items": [supplier_public_view(item) for item in items]}


@router.get("/api/v1/operator/supplier-sources")
def list_supplier_sources(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = _service(session)
    return {"items": [_source_registry_view(item) for item in service.list_source_registries()]}


@router.post("/api/v1/admin/supplier-sources")
def create_supplier_source(
    payload: SupplierSourceCreatePayload,
    auth: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    item = _service(session).create_source_registry(
        label=payload.label,
        adapter_key=payload.adapter_key,
        config_json=payload.config_json,
        auth=auth,
        reason_code=payload.reason_code,
    )
    return {"item": _source_registry_view(item)}


@router.get("/api/v1/operator/supplier-ingests")
def list_supplier_ingests(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    registries = {
        item.id: item
        for item in session.scalars(select(SupplierSourceRegistry)).all()
    }
    items = session.scalars(select(SupplierRawIngest).order_by(SupplierRawIngest.created_at.desc())).all()
    return {"items": [_ingest_view(item, registries.get(item.source_registry_id)) for item in items]}


@router.post("/api/v1/operator/supplier-ingests/run-inline")
def run_supplier_ingest_inline(
    payload: SupplierIngestPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        summary = _service(session).run_ingest(
            source_registry_code=payload.source_registry_code,
            idempotency_key=payload.idempotency_key,
            auth=auth,
            reason_code=payload.reason_code,
            trigger_mode="inline",
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": _ingest_summary_view(summary)}


@router.post("/api/v1/operator/supplier-ingests/enqueue")
def enqueue_supplier_ingest(
    payload: SupplierIngestPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        registry = _service(session).get_source_registry_by_code(payload.source_registry_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    task = run_supplier_ingest.delay(
        payload.source_registry_code,
        payload.idempotency_key,
        payload.reason_code,
        "job",
    )
    ingest = session.scalar(select(SupplierRawIngest).where(SupplierRawIngest.idempotency_key == payload.idempotency_key))
    if ingest is not None:
        ingest.task_id = task.id
        ingest.trigger_mode = "job"
    return {
        "task_id": task.id,
        "source_registry": _source_registry_view(registry),
        "idempotency_key": payload.idempotency_key,
        "status": "queued",
    }


@router.get("/api/v1/operator/supplier-ingests/{ingest_code}")
def get_supplier_ingest(
    ingest_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    ingest = session.scalar(select(SupplierRawIngest).where(SupplierRawIngest.code == ingest_code))
    if ingest is None:
        raise HTTPException(status_code=404, detail="supplier_ingest_not_found")
    registry = session.get(SupplierSourceRegistry, ingest.source_registry_id)
    raw_records = session.scalars(select(SupplierRawRecord).where(SupplierRawRecord.ingest_id == ingest.id).order_by(SupplierRawRecord.created_at.asc())).all()
    normalizations = {
        item.raw_record_id: item
        for item in session.scalars(select(SupplierNormalizationResult).where(SupplierNormalizationResult.ingest_id == ingest.id)).all()
    }
    candidates = session.scalars(select(SupplierDedupCandidate).where(SupplierDedupCandidate.ingest_id == ingest.id).order_by(SupplierDedupCandidate.created_at.asc())).all()
    return {
        "ingest": _ingest_view(ingest, registry),
        "raw_records": [_raw_record_view(item, normalizations.get(item.id)) for item in raw_records],
        "dedup_candidates": [
            _candidate_view(
                item,
                normalization=session.get(SupplierNormalizationResult, item.normalization_result_id),
                supplier=session.get(SupplierCompany, item.matched_supplier_company_id),
            )
            for item in candidates
        ],
    }


def _ingest_summary_view(summary: SupplierIngestSummary) -> dict[str, object]:
    return {
        "ingest_code": summary.ingest_code,
        "ingest_status": summary.ingest_status,
        "source_registry_code": summary.source_registry_code,
        "raw_count": summary.raw_count,
        "normalized_count": summary.normalized_count,
        "merged_count": summary.merged_count,
        "candidate_count": summary.candidate_count,
        "replayed": summary.replayed,
    }


@router.get("/api/v1/operator/supplier-raw")
def list_supplier_raw(
    ingest_code: str | None = None,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    stmt = select(SupplierRawRecord).order_by(SupplierRawRecord.created_at.desc())
    if ingest_code:
        ingest = session.scalar(select(SupplierRawIngest).where(SupplierRawIngest.code == ingest_code))
        if ingest is None:
            raise HTTPException(status_code=404, detail="supplier_ingest_not_found")
        stmt = stmt.where(SupplierRawRecord.ingest_id == ingest.id)
    items = session.scalars(stmt).all()
    normalizations = {
        item.raw_record_id: item
        for item in session.scalars(select(SupplierNormalizationResult).where(SupplierNormalizationResult.raw_record_id.in_([row.id for row in items]))).all()
    } if items else {}
    return {"items": [_raw_record_view(item, normalizations.get(item.id)) for item in items]}


@router.get("/api/v1/operator/suppliers")
def list_suppliers(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    items = session.scalars(select(SupplierCompany).where(SupplierCompany.deleted_at.is_(None)).order_by(SupplierCompany.created_at.asc())).all()
    return {"items": [supplier_operator_view(item) for item in items]}


@router.post("/api/v1/admin/suppliers")
def create_supplier(
    payload: SupplierCreatePayload,
    auth: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    supplier = _service(session).create_manual_supplier(
        display_name=payload.display_name,
        legal_name=payload.legal_name,
        canonical_email=payload.canonical_email,
        canonical_phone=payload.canonical_phone,
        website=payload.website,
        capability_summary=payload.capability_summary,
        capabilities_json=payload.capabilities_json,
        address_text=payload.address_text,
        city=payload.city,
        district=payload.district,
        country_code=payload.country_code,
        auth=auth,
        reason_code=payload.reason_code,
    )
    return {"item": supplier_operator_view(supplier)}


@router.get("/api/v1/operator/suppliers/{supplier_code}")
def get_supplier_detail(
    supplier_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    supplier = session.scalar(select(SupplierCompany).where(SupplierCompany.code == supplier_code))
    if supplier is None:
        raise HTTPException(status_code=404, detail="supplier_not_found")
    return _supplier_detail_view(session, supplier)


@router.get("/api/v1/operator/supplier-sites/{site_code}")
def get_supplier_site_detail(
    site_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    site = session.scalar(select(SupplierSite).where(SupplierSite.code == site_code))
    if site is None:
        raise HTTPException(status_code=404, detail="supplier_site_not_found")
    supplier = session.get(SupplierCompany, site.supplier_company_id)
    address = session.get(CompanyAddress, site.address_id) if site.address_id else None
    ratings = session.scalars(
        select(SupplierRatingSnapshot).where(SupplierRatingSnapshot.supplier_site_id == site.id).order_by(SupplierRatingSnapshot.captured_at.desc())
    ).all()
    return {
        "site": supplier_site_view(site),
        "supplier": supplier_operator_view(supplier) if supplier else None,
        "address": company_address_view(address) if address else None,
        "rating_history": [_rating_view(item) for item in ratings],
    }


@router.post("/api/v1/operator/suppliers/{supplier_code}/verify")
def verify_supplier(
    supplier_code: str,
    payload: SupplierVerifyPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        supplier = _service(session).apply_trust_transition(
            supplier_code=supplier_code,
            target_trust_level=payload.target_trust_level,
            auth=auth,
            reason_code=payload.reason_code,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"item": supplier_operator_view(supplier)}


@router.post("/api/v1/admin/suppliers/{supplier_code}/block")
def block_supplier(
    supplier_code: str,
    payload: SupplierStatusPayload,
    auth: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        supplier = _service(session).block_supplier(
            supplier_code=supplier_code,
            auth=auth,
            reason_code=payload.reason_code,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": supplier_operator_view(supplier)}


@router.post("/api/v1/admin/suppliers/{supplier_code}/archive")
def archive_supplier(
    supplier_code: str,
    payload: SupplierStatusPayload,
    auth: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        supplier = _service(session).archive_supplier(
            supplier_code=supplier_code,
            auth=auth,
            reason_code=payload.reason_code,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": supplier_operator_view(supplier)}


@router.get("/api/v1/operator/supplier-dedup-candidates")
def list_supplier_dedup_candidates(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    items = session.scalars(
        select(SupplierDedupCandidate).where(SupplierDedupCandidate.deleted_at.is_(None)).order_by(SupplierDedupCandidate.created_at.desc())
    ).all()
    return {
        "items": [
            _candidate_view(
                item,
                normalization=session.get(SupplierNormalizationResult, item.normalization_result_id),
                supplier=session.get(SupplierCompany, item.matched_supplier_company_id),
            )
            for item in items
        ]
    }


@router.post("/api/v1/operator/supplier-dedup-candidates/{candidate_code}/decision")
def resolve_supplier_dedup_candidate(
    candidate_code: str,
    payload: SupplierDedupDecisionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        candidate = _service(session).resolve_dedup_candidate(
            candidate_code=candidate_code,
            decision=payload.decision,
            auth=auth,
            reason_code=payload.reason_code,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    normalization = session.get(SupplierNormalizationResult, candidate.normalization_result_id)
    supplier = session.get(SupplierCompany, candidate.matched_supplier_company_id)
    return {"item": _candidate_view(candidate, normalization, supplier)}
