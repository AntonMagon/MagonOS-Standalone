# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles
from ..offer_services import OfferCurrentBundle, OfferService
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from .shared import (
    offer_comparison_metadata_view,
    offer_confirmation_view,
    offer_operator_view,
    offer_reset_reason_view,
    offer_version_view,
    request_operator_view,
)

router = APIRouter(tags=["Offers"])


class OfferUpsertPayload(BaseModel):
    amount: float | None = None
    currency_code: str = "VND"
    lead_time_days: int | None = None
    terms_text: str | None = None
    scenario_type: str = "standard"
    supplier_ref: str | None = None
    public_summary: str | None = None
    comparison_title: str | None = None
    comparison_rank: int | None = None
    recommended: bool = False
    highlights: list[str] | None = None
    metadata: dict | None = None
    reason_code: str = Field(min_length=3)
    note: str | None = None


class OfferActionPayload(BaseModel):
    reason_code: str = Field(min_length=3)
    note: str | None = None


def _bundle_view(bundle: OfferCurrentBundle) -> dict[str, object]:
    return {
        "offer": offer_operator_view(bundle.offer),
        "current_version": offer_version_view(bundle.version),
        "comparison": offer_comparison_metadata_view(bundle.comparison) if bundle.comparison else None,
    }


def _offer_detail_payload(service: OfferService, offer_code: str) -> dict[str, object]:
    offer = service.get_offer_by_code(offer_code)
    current_version = service.get_current_version(offer)
    comparison = service.get_comparison_metadata(current_version.id)
    request = service.get_request_by_code(offer.request_ref)
    return {
        "item": offer_operator_view(offer),
        "request": request_operator_view(request),
        "current_version": offer_version_view(current_version),
        "versions": [offer_version_view(item) for item in service.list_versions(offer.id)],
        "confirmations": [offer_confirmation_view(item) for item in service.list_confirmations(offer.id)],
        "comparison": offer_comparison_metadata_view(comparison) if comparison else None,
        "reset_reasons": [offer_reset_reason_view(item) for item in service.list_reset_reasons(offer.id)],
    }


def _compare_payload(service: OfferService, request_code: str, *, public: bool) -> dict[str, object]:
    request = service.get_request_by_code(request_code)
    offers = []
    for offer in service.list_request_offers(request.id):
        current_version = service.get_current_version(offer)
        comparison = service.get_comparison_metadata(current_version.id)
        if public and offer.offer_status not in {"sent", "accepted", "declined", "expired"}:
            continue
        offers.append(
            {
                "offer": offer_operator_view(offer),
                "current_version": offer_version_view(current_version),
                "comparison": offer_comparison_metadata_view(comparison) if comparison else None,
            }
        )
    offers.sort(key=lambda item: (item["comparison"]["comparison_rank"] if item["comparison"] and item["comparison"]["comparison_rank"] is not None else 9999, item["offer"]["code"]))
    return {
        "request": request_operator_view(request),
        "items": offers,
    }


@router.get("/api/v1/operator/offers")
def operator_offers(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    service = OfferService(session)
    return {"items": [offer_operator_view(item) for item in service.list_offers()]}


@router.get("/api/v1/operator/offers/{offer_code}")
def operator_offer_detail(offer_code: str, _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    service = OfferService(session)
    try:
        return _offer_detail_payload(service, offer_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/v1/operator/requests/{request_code}/offers/compare")
def operator_offer_compare(request_code: str, _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    service = OfferService(session)
    try:
        return _compare_payload(service, request_code, public=False)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/v1/operator/requests/{request_code}/offers")
def create_offer(
    request_code: str,
    payload: OfferUpsertPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OfferService(session)
    try:
        request = service.get_request_by_code(request_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bundle = service.create_offer(
        request=request,
        amount=payload.amount,
        currency_code=payload.currency_code,
        lead_time_days=payload.lead_time_days,
        terms_text=payload.terms_text,
        scenario_type=payload.scenario_type,
        supplier_ref=payload.supplier_ref,
        public_summary=payload.public_summary,
        comparison_title=payload.comparison_title,
        comparison_rank=payload.comparison_rank,
        recommended=payload.recommended,
        highlights=payload.highlights,
        metadata=payload.metadata,
        auth=auth,
        reason_code=payload.reason_code,
        note=payload.note,
    )
    return _bundle_view(bundle)


@router.post("/api/v1/operator/offers/{offer_code}/revise")
def revise_offer(
    offer_code: str,
    payload: OfferUpsertPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OfferService(session)
    try:
        offer = service.get_offer_by_code(offer_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bundle = service.revise_offer(
        offer=offer,
        amount=payload.amount,
        currency_code=payload.currency_code,
        lead_time_days=payload.lead_time_days,
        terms_text=payload.terms_text,
        scenario_type=payload.scenario_type,
        supplier_ref=payload.supplier_ref,
        public_summary=payload.public_summary,
        comparison_title=payload.comparison_title,
        comparison_rank=payload.comparison_rank,
        recommended=payload.recommended,
        highlights=payload.highlights,
        metadata=payload.metadata,
        auth=auth,
        reason_code=payload.reason_code,
        note=payload.note,
    )
    return _bundle_view(bundle)


@router.post("/api/v1/operator/offers/{offer_code}/send")
def send_offer(
    offer_code: str,
    payload: OfferActionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OfferService(session)
    try:
        offer = service.get_offer_by_code(offer_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bundle = service.send_offer(offer=offer, auth=auth, reason_code=payload.reason_code, note=payload.note)
    return _bundle_view(bundle)


@router.post("/api/v1/operator/offers/{offer_code}/accept")
def operator_accept_offer(
    offer_code: str,
    payload: OfferActionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OfferService(session)
    try:
        offer = service.get_offer_by_code(offer_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bundle = service.record_confirmation(offer=offer, action="accept", auth=auth, reason_code=payload.reason_code, note=payload.note)
    return _bundle_view(bundle)


@router.post("/api/v1/operator/offers/{offer_code}/decline")
def operator_decline_offer(
    offer_code: str,
    payload: OfferActionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OfferService(session)
    try:
        offer = service.get_offer_by_code(offer_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bundle = service.record_confirmation(offer=offer, action="decline", auth=auth, reason_code=payload.reason_code, note=payload.note)
    return _bundle_view(bundle)


@router.post("/api/v1/operator/offers/{offer_code}/expire")
def operator_expire_offer(
    offer_code: str,
    payload: OfferActionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OfferService(session)
    try:
        offer = service.get_offer_by_code(offer_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bundle = service.record_confirmation(offer=offer, action="expire", auth=auth, reason_code=payload.reason_code, note=payload.note)
    return _bundle_view(bundle)


@router.get("/api/v1/public/requests/{customer_ref}/offers/compare")
def public_offer_compare(customer_ref: str, session: Session = Depends(get_db)) -> dict[str, object]:
    service = OfferService(session)
    try:
        request = service.get_request_by_customer_ref(customer_ref)
        return _compare_payload(service, request.code, public=True)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/v1/public/requests/{customer_ref}/offers/{offer_code}/accept")
def public_accept_offer(customer_ref: str, offer_code: str, payload: OfferActionPayload, session: Session = Depends(get_db)) -> dict[str, object]:
    service = OfferService(session)
    try:
        bundle = service.public_confirm_offer(
            customer_ref=customer_ref,
            offer_code=offer_code,
            action="accept",
            reason_code=payload.reason_code,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _bundle_view(bundle)


@router.post("/api/v1/public/requests/{customer_ref}/offers/{offer_code}/decline")
def public_decline_offer(customer_ref: str, offer_code: str, payload: OfferActionPayload, session: Session = Depends(get_db)) -> dict[str, object]:
    service = OfferService(session)
    try:
        bundle = service.public_confirm_offer(
            customer_ref=customer_ref,
            offer_code=offer_code,
            action="decline",
            reason_code=payload.reason_code,
            note=payload.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _bundle_view(bundle)
