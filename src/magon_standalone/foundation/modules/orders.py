from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_db, require_roles
from ..file_document_services import FileDocumentService
from ..models import AuditEvent, DocumentVersion, FileVersion, PaymentRecord, RequestRecord
from ..offer_services import OfferService
from ..order_services import ORDER_ACTIONS, OrderService
from ..request_intake_services import RequestIntakeService
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from .shared import document_view, file_asset_view, ledger_entry_view, order_line_view, order_operator_view, payment_record_view, timeline_event_view

router = APIRouter(tags=["Orders"])


class OrderConversionPayload(BaseModel):
    reason_code: str = Field(min_length=3)
    note: str | None = None


class OrderActionPayload(BaseModel):
    action: str
    reason_code: str = Field(min_length=3)
    note: str | None = None
    supplier_ref: str | None = None
    line_codes: list[str] | None = None


class PaymentCreatePayload(BaseModel):
    amount: float | None = None
    currency_code: str = "VND"
    payment_ref: str | None = None
    provider_ref: str | None = None
    reason_code: str = Field(min_length=3)
    note: str | None = None


class PaymentTransitionPayload(BaseModel):
    target_state: str
    reason_code: str = Field(min_length=3)
    note: str | None = None


@router.get("/api/v1/operator/orders")
def operator_orders(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    service = OrderService(session)
    items = service.list_orders()
    return {"items": [order_operator_view(item) for item in items]}


@router.get("/api/v1/operator/orders/{order_code}")
def operator_order_detail(
    order_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OrderService(session)
    intake_service = RequestIntakeService(session)
    try:
        order = service.get_order_by_code(order_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    file_service = FileDocumentService(session)
    payments = service.list_payment_records(order.id)
    payment_codes = [item.code for item in payments]
    timeline_query = select(AuditEvent).where((AuditEvent.entity_type == "order") & (AuditEvent.entity_id == order.id))
    if payment_codes:
        timeline_query = timeline_query.union_all(
            select(AuditEvent).where((AuditEvent.entity_type == "payment_record") & (AuditEvent.entity_code.in_(payment_codes)))
        )
        timeline_items = session.scalars(select(AuditEvent).from_statement(timeline_query.order_by(AuditEvent.created_at.asc()))).all()
    else:
        timeline_items = session.scalars(timeline_query.order_by(AuditEvent.created_at.asc())).all()
    files = []
    for asset in file_service.list_files_for_owner("order", order.id):
        latest_version = session.scalar(select(FileVersion).where(FileVersion.id == asset.latest_version_id)) if asset.latest_version_id else None
        checks = file_service.list_file_checks(latest_version.id) if latest_version else []
        files.append(
            file_asset_view(
                asset,
                latest_version=latest_version,
                checks=checks,
                download_url=f"/platform-api/api/v1/operator/file-versions/{latest_version.code}/download" if latest_version else None,
            )
        )
    documents = []
    for document in file_service.list_documents_for_owner("order", order.id):
        current_version = session.scalar(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.version_no == document.current_version_no,
                DocumentVersion.deleted_at.is_(None),
            )
        )
        documents.append(
            document_view(
                document,
                current_version=current_version,
                download_url=f"/platform-api/api/v1/operator/document-versions/{current_version.code}/download" if current_version else None,
            )
        )
    return {
        "item": order_operator_view(order),
        "lines": [order_line_view(item) for item in service.list_order_lines(order.id)],
        "payments": [payment_record_view(item) for item in payments],
        "ledger": [ledger_entry_view(item) for item in service.list_ledger_entries(order.id)],
        "files": files,
        "documents": documents,
        # RU: order timeline читается из общего audit-trail, чтобы не плодить второй event-store только ради заказов.
        "timeline": [timeline_event_view(item) for item in timeline_items],
    }


@router.post("/api/v1/operator/offers/{offer_code}/convert-to-order")
def convert_offer_to_order(
    offer_code: str,
    payload: OrderConversionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    offer_service = OfferService(session)
    order_service = OrderService(session)
    try:
        offer = offer_service.get_offer_by_code(offer_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    request = session.scalar(select(RequestRecord).where(RequestRecord.id == offer.request_id))
    if request is None:
        raise HTTPException(status_code=404, detail="request_not_found")
    version = offer_service.get_current_version(offer)
    if version.confirmation_state != "accepted":
        raise HTTPException(status_code=409, detail="offer_version_not_confirmed")
    if request.request_status != "offer_sent":
        raise HTTPException(status_code=409, detail="request_not_ready_for_order")
    bundle = order_service.create_order_from_offer(
        offer=offer,
        version=version,
        request=request,
        auth=auth,
        reason_code=payload.reason_code,
        note=payload.note,
    )
    return {
        "item": order_operator_view(bundle.order),
        "lines": [order_line_view(item) for item in bundle.lines],
        "payments": [payment_record_view(item) for item in bundle.payments],
        "ledger": [ledger_entry_view(item) for item in bundle.ledger],
    }


@router.post("/api/v1/operator/orders/{order_code}/action")
def apply_order_action(
    order_code: str,
    payload: OrderActionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    if payload.action not in ORDER_ACTIONS:
        raise HTTPException(status_code=422, detail="order_action_invalid")
    service = OrderService(session)
    try:
        order = service.get_order_by_code(order_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bundle = service.apply_order_action(
        order=order,
        action=payload.action,
        auth=auth,
        reason_code=payload.reason_code,
        note=payload.note,
        supplier_ref=payload.supplier_ref,
        line_codes=payload.line_codes,
    )
    return {
        "item": order_operator_view(bundle.order),
        "lines": [order_line_view(item) for item in bundle.lines],
        "payments": [payment_record_view(item) for item in bundle.payments],
        "ledger": [ledger_entry_view(item) for item in bundle.ledger],
    }


@router.post("/api/v1/operator/orders/{order_code}/payments")
def create_order_payment(
    order_code: str,
    payload: PaymentCreatePayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OrderService(session)
    try:
        order = service.get_order_by_code(order_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    item = service.create_payment_record(
        order=order,
        amount=payload.amount,
        currency_code=payload.currency_code,
        payment_ref=payload.payment_ref,
        provider_ref=payload.provider_ref,
        reason_code=payload.reason_code,
        note=payload.note,
        auth=auth,
    )
    return {"item": payment_record_view(item)}


@router.post("/api/v1/operator/payment-records/{payment_code}/transition")
def transition_payment_record(
    payment_code: str,
    payload: PaymentTransitionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = OrderService(session)
    payment = session.scalar(select(PaymentRecord).where(PaymentRecord.code == payment_code, PaymentRecord.deleted_at.is_(None)))
    if payment is None:
        raise HTTPException(status_code=404, detail="payment_record_not_found")
    bundle = service.transition_payment_record(
        payment=payment,
        target_state=payload.target_state,
        reason_code=payload.reason_code,
        note=payload.note,
        auth=auth,
    )
    return {
        "order": order_operator_view(bundle.order),
        "payments": [payment_record_view(item) for item in bundle.payments],
        "ledger": [ledger_entry_view(item) for item in bundle.ledger],
    }
