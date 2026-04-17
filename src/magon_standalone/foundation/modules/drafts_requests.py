# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_auth_context, get_db, require_roles
from ..file_document_services import FileDocumentService
from ..models import CatalogItem, Company, DocumentVersion, DraftRequest, FileVersion, OrderRecord, RequestFollowUpItem, RequestReason, RequestRecord
from ..request_intake_services import DRAFT_STATUSES, FOLLOW_UP_STATUSES, RequestIntakeService
from ..security import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_OPERATOR, AuthContext
from ..workflow_support import WorkflowSupportService
from .shared import (
    clarification_cycle_view,
    draft_public_view,
    follow_up_item_view,
    intake_file_link_view,
    file_asset_view,
    document_view,
    order_public_view,
    request_operator_view,
    request_reason_view,
    required_field_state_view,
    timeline_event_view,
)

router = APIRouter(tags=["DraftsRequests"])


class DraftCreatePayload(BaseModel):
    customer_email: EmailStr | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    guest_company_name: str | None = None
    company_code: str | None = None
    catalog_item_code: str | None = None
    title: str | None = None
    summary: str | None = None
    item_service_context: str | None = None
    city: str | None = None
    geo: dict | None = None
    source_channel: str | None = None
    intake_channel: str = "web_public"
    locale_code: str = "ru"
    requested_deadline_at: datetime | None = None
    honeypot: str | None = None
    elapsed_ms: int = Field(ge=0, default=0)


class DraftUpdatePayload(BaseModel):
    title: str | None = None
    summary: str | None = None
    customer_name: str | None = None
    customer_email: EmailStr | None = None
    customer_phone: str | None = None
    guest_company_name: str | None = None
    item_service_context: str | None = None
    city: str | None = None
    geo: dict | None = None
    requested_deadline_at: datetime | None = None
    locale_code: str | None = None
    source_channel: str | None = None


class DraftSubmitPayload(BaseModel):
    reason_code: str = Field(min_length=3)
    note: str | None = None


class FileLinkPayload(BaseModel):
    label: str = Field(min_length=2)
    file_url: str = Field(min_length=8)
    visibility: str = "role"
    reason_code: str = Field(min_length=3)


class DraftStatusPayload(BaseModel):
    target_status: str
    reason_code: str = Field(min_length=3)
    note: str | None = None


class RequestTransitionPayload(BaseModel):
    target_status: str
    reason_code: str = Field(min_length=3)
    note: str | None = None
    owner_user_code: str | None = None
    assignee_user_code: str | None = None


class RequestReasonPayload(BaseModel):
    reason_kind: str
    reason_code: str = Field(min_length=3)
    note: str | None = None


class FollowUpCreatePayload(BaseModel):
    title: str = Field(min_length=2)
    detail: str | None = None
    due_at: datetime | None = None
    owner_user_code: str | None = None
    customer_visible: bool = False
    reason_code: str = Field(min_length=3)


class FollowUpTransitionPayload(BaseModel):
    target_status: str
    reason_code: str = Field(min_length=3)


class ReasonResolvePayload(BaseModel):
    reason_code: str = Field(min_length=3)


def _find_company(session: Session, company_code: str | None) -> Company | None:
    if not company_code:
        return None
    return session.scalar(select(Company).where(Company.code == company_code))


def _find_catalog_item(session: Session, catalog_item_code: str | None) -> CatalogItem | None:
    if not catalog_item_code:
        return None
    return session.scalar(select(CatalogItem).where(CatalogItem.code == catalog_item_code, CatalogItem.deleted_at.is_(None)))


def _validate_antibot(payload: DraftCreatePayload) -> None:
    if payload.honeypot and payload.honeypot.strip():
        raise HTTPException(status_code=422, detail="antibot_rejected")
    if payload.elapsed_ms < 1200:
        raise HTTPException(status_code=422, detail="antibot_elapsed_too_short")
    if (payload.source_channel or payload.intake_channel) not in {"web_public", "catalog_ready", "catalog_config", "rfq_public"}:
        raise HTTPException(status_code=422, detail="draft_intake_channel_invalid")


def _resolve_source_channel(payload: DraftCreatePayload) -> str:
    return payload.source_channel or payload.intake_channel or "web_public"


def _draft_detail(service: RequestIntakeService, draft: DraftRequest) -> dict[str, object]:
    submitted_request = service.session.scalar(select(RequestRecord).where(RequestRecord.id == draft.submitted_request_id)) if draft.submitted_request_id else None
    return {
        **draft_public_view(draft),
        "submitted_request_customer_ref": submitted_request.customer_ref if submitted_request else None,
        "required_fields_state": [required_field_state_view(item) for item in service.list_required_fields("draft_request", draft.id)],
        "file_links": [intake_file_link_view(item) for item in service.list_file_links("draft_request", draft.id)],
        "timeline": [timeline_event_view(item) for item in service.list_timeline_events(entity_type="draft_request", entity_id=draft.id)],
    }


def _request_detail(service: RequestIntakeService, request_record, *, customer_visible_only: bool = False) -> dict[str, object]:
    order = service.session.scalar(
        select(OrderRecord).where(OrderRecord.request_id == request_record.id, OrderRecord.deleted_at.is_(None)).order_by(OrderRecord.created_at.desc())
    )
    file_service = FileDocumentService(service.session)
    workflow = WorkflowSupportService(service.session)
    managed_files = []
    for asset in file_service.list_request_related_files(request_record, customer_visible_only=customer_visible_only):
        latest_version = service.session.scalar(select(FileVersion).where(FileVersion.id == asset.latest_version_id)) if asset.latest_version_id else None
        checks = file_service.list_file_checks(latest_version.id) if latest_version and not customer_visible_only else []
        download_url = None
        if latest_version:
            if customer_visible_only:
                download_url = f"/platform-api/api/v1/public/requests/{request_record.customer_ref}/files/{latest_version.code}/download"
            else:
                download_url = f"/platform-api/api/v1/operator/file-versions/{latest_version.code}/download"
        managed_files.append(file_asset_view(asset, latest_version=latest_version, checks=checks, download_url=download_url))
    managed_documents = []
    for document in file_service.list_request_related_documents(request_record, customer_visible_only=customer_visible_only):
        current_version = service.session.scalar(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document.id,
                DocumentVersion.version_no == document.current_version_no,
                DocumentVersion.deleted_at.is_(None),
            )
        )
        download_url = None
        if current_version:
            if customer_visible_only:
                download_url = f"/platform-api/api/v1/public/requests/{request_record.customer_ref}/documents/{current_version.code}/download"
            else:
                download_url = f"/platform-api/api/v1/operator/document-versions/{current_version.code}/download"
        managed_documents.append(document_view(document, current_version=current_version, download_url=download_url))
    return {
        **request_operator_view(request_record),
        "reasons": [request_reason_view(item) for item in service.list_request_reasons(request_record.id)],
        "clarification_cycles": [clarification_cycle_view(item) for item in service.list_clarification_cycles(request_record.id)],
        "follow_up_items": [follow_up_item_view(item) for item in service.list_follow_up_items(request_record.id)],
        "file_links": [intake_file_link_view(item) for item in service.list_file_links("request", request_record.id)],
        "managed_files": managed_files,
        "documents": managed_documents,
        "order": order_public_view(order) if order else None,
        "notifications": [
            {**timeline_event_view(item), "reason_display": workflow.reason_display(item.reason_code)}
            for item in workflow.list_timeline(
                owner_type="request",
                owner_id=request_record.id,
                audience=ROLE_CUSTOMER if customer_visible_only else ROLE_OPERATOR,
            )
            if item.entry_kind == "notification"
        ],
        "timeline": [
            {**timeline_event_view(item), "reason_display": workflow.reason_display(getattr(item, "reason_code", None))}
            for item in workflow.list_timeline(
                owner_type="request",
                owner_id=request_record.id,
                audience=ROLE_CUSTOMER if customer_visible_only else ROLE_OPERATOR,
            )
        ],
    }


@router.post("/api/v1/public/draft-requests")
def create_public_draft(payload: DraftCreatePayload, auth: AuthContext = Depends(get_auth_context), session: Session = Depends(get_db)) -> dict[str, object]:
    _validate_antibot(payload)
    service = RequestIntakeService(session)
    company = _find_company(session, payload.company_code)
    catalog_item = _find_catalog_item(session, payload.catalog_item_code)
    if payload.catalog_item_code and catalog_item is None:
        raise HTTPException(status_code=404, detail="catalog_item_not_found")
    draft = service.create_draft(
        customer_email=payload.customer_email,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        guest_company_name=payload.guest_company_name,
        company_id=company.id if company else None,
        catalog_item_id=catalog_item.id if catalog_item else None,
        title=payload.title,
        summary=payload.summary,
        item_service_context=payload.item_service_context,
        city=payload.city,
        geo_json=payload.geo,
        source_channel=_resolve_source_channel(payload),
        intake_channel=payload.intake_channel,
        locale_code=payload.locale_code,
        requested_deadline_at=payload.requested_deadline_at,
        auth=auth,
        reason_code=f"public_create:{_resolve_source_channel(payload)}",
        reason_note="Public draft entry created.",
    )
    return {"item": _draft_detail(service, draft)}


@router.get("/api/v1/public/draft-requests/{draft_code}")
def get_public_draft(draft_code: str, session: Session = Depends(get_db)) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        draft = service.get_draft_by_code(draft_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": _draft_detail(service, draft)}


@router.patch("/api/v1/public/draft-requests/{draft_code}")
def update_public_draft(
    draft_code: str,
    payload: DraftUpdatePayload,
    auth: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        draft = service.get_draft_by_code(draft_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    updates = payload.model_dump(exclude_unset=True)
    service.update_draft(
        draft,
        title=updates.get("title", draft.title),
        summary=updates.get("summary", draft.summary),
        customer_name=updates.get("customer_name", draft.customer_name),
        customer_email=updates.get("customer_email", draft.customer_email),
        customer_phone=updates.get("customer_phone", draft.customer_phone),
        guest_company_name=updates.get("guest_company_name", draft.guest_company_name),
        item_service_context=updates.get("item_service_context", draft.item_service_context),
        city=updates.get("city", draft.city),
        geo_json=updates.get("geo", draft.geo_json),
        requested_deadline_at=updates.get("requested_deadline_at", draft.requested_deadline_at),
        locale_code=updates.get("locale_code", draft.locale_code),
        source_channel=updates.get("source_channel", draft.source_channel),
        auth=auth,
        reason_code="draft_autosave",
        reason_note="Public draft autosave.",
    )
    return {"item": _draft_detail(service, draft)}


@router.post("/api/v1/public/draft-requests/{draft_code}/file-links")
def add_public_draft_file_link(
    draft_code: str,
    payload: FileLinkPayload,
    auth: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        draft = service.get_draft_by_code(draft_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    item = service.add_file_link(
        owner_type="draft_request",
        owner_id=draft.id,
        label=payload.label,
        file_url=payload.file_url,
        visibility=payload.visibility,
        auth=auth,
        reason_code=payload.reason_code,
    )
    return {"item": intake_file_link_view(item)}


@router.post("/api/v1/public/draft-requests/{draft_code}/submit")
def submit_public_draft(
    draft_code: str,
    payload: DraftSubmitPayload,
    auth: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        draft = service.get_draft_by_code(draft_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    request_record = service.submit_draft(draft, auth=auth if auth.is_authenticated else None, reason_code=payload.reason_code, reason_note=payload.note)
    return {"draft": _draft_detail(service, draft), "request": _request_detail(service, request_record)}


@router.post("/api/v1/public/draft-requests/{draft_code}/abandon")
def abandon_public_draft(
    draft_code: str,
    payload: DraftStatusPayload,
    auth: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        draft = service.get_draft_by_code(draft_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    service.set_draft_status(draft, target_status="abandoned", auth=auth if auth.is_authenticated else None, reason_code=payload.reason_code, reason_note=payload.note)
    return {"item": _draft_detail(service, draft)}


@router.get("/api/v1/public/requests/{customer_ref}")
def get_public_request(customer_ref: str, session: Session = Depends(get_db)) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        request_record = service.get_request_by_customer_ref(customer_ref)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload = _request_detail(service, request_record, customer_visible_only=True)
    payload["reasons"] = [item for item in payload["reasons"] if item["reason_kind"] == "reason"]
    payload["follow_up_items"] = [item for item in payload["follow_up_items"] if item["customer_visible"]]
    payload["file_links"] = [item for item in payload["file_links"] if item["visibility"] in {"public", "customer"}]
    payload["timeline"] = [
        item
        for item in payload["timeline"]
        if item["action"] in {"request_created", "request_status_changed", "clarification_cycle_opened", "follow_up_item_created"}
    ]
    return {"item": payload}


@router.get("/api/v1/operator/draft-requests")
def operator_drafts(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    service = RequestIntakeService(session)
    return {"items": [_draft_detail(service, item) for item in service.list_drafts()]}


@router.get("/api/v1/operator/draft-requests/{draft_code}")
def operator_draft_detail(
    draft_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        draft = service.get_draft_by_code(draft_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": _draft_detail(service, draft)}


@router.post("/api/v1/operator/draft-requests/{draft_code}/submit")
def submit_draft(
    draft_code: str,
    payload: DraftSubmitPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        draft = service.get_draft_by_code(draft_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    request_record = service.submit_draft(draft, auth=auth, reason_code=payload.reason_code, reason_note=payload.note)
    return {"draft": _draft_detail(service, draft), "request": _request_detail(service, request_record)}


@router.post("/api/v1/operator/draft-requests/{draft_code}/transition")
def transition_draft(
    draft_code: str,
    payload: DraftStatusPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    if payload.target_status not in DRAFT_STATUSES:
        raise HTTPException(status_code=422, detail="draft_status_invalid")
    service = RequestIntakeService(session)
    try:
        draft = service.get_draft_by_code(draft_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    service.set_draft_status(draft, target_status=payload.target_status, auth=auth, reason_code=payload.reason_code, reason_note=payload.note)
    return {"item": _draft_detail(service, draft)}


@router.get("/api/v1/operator/requests")
def operator_requests(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    service = RequestIntakeService(session)
    return {"items": [request_operator_view(item) for item in service.list_requests()]}


@router.get("/api/v1/operator/requests/{request_code}")
def operator_request_detail(
    request_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        request_record = service.get_request_by_code(request_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"item": _request_detail(service, request_record)}


@router.post("/api/v1/operator/requests/{request_code}/transition")
def transition_request(
    request_code: str,
    payload: RequestTransitionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        request_record = service.get_request_by_code(request_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    owner = service.get_user_by_code(payload.owner_user_code)
    assignee = service.get_user_by_code(payload.assignee_user_code)
    service.transition_request(
        request_record,
        target_status=payload.target_status,
        reason_code=payload.reason_code,
        reason_note=payload.note,
        auth=auth,
        owner_user_id=owner.id if owner else None,
        assignee_user_id=assignee.id if assignee else None,
    )
    return {"item": _request_detail(service, request_record)}


@router.post("/api/v1/operator/requests/{request_code}/reasons")
def add_request_reason(
    request_code: str,
    payload: RequestReasonPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        request_record = service.get_request_by_code(request_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    item = service.add_request_reason(
        request=request_record,
        reason_kind=payload.reason_kind,
        reason_code=payload.reason_code,
        note=payload.note,
        auth=auth,
    )
    return {"item": request_reason_view(item)}


@router.post("/api/v1/operator/request-reasons/{request_reason_code}/resolve")
def resolve_request_reason(
    request_reason_code: str,
    payload: ReasonResolvePayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    item = session.scalar(select(RequestReason).where(RequestReason.code == request_reason_code, RequestReason.deleted_at.is_(None)))
    if item is None:
        raise HTTPException(status_code=404, detail="request_reason_not_found")
    service.resolve_request_reason(item, reason_code=payload.reason_code, auth=auth)
    return {"item": request_reason_view(item)}


@router.post("/api/v1/operator/requests/{request_code}/follow-up-items")
def add_request_follow_up(
    request_code: str,
    payload: FollowUpCreatePayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        request_record = service.get_request_by_code(request_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    owner = service.get_user_by_code(payload.owner_user_code)
    item = service.add_follow_up_item(
        request=request_record,
        title=payload.title,
        detail=payload.detail,
        due_at=payload.due_at,
        owner_user_id=owner.id if owner else None,
        customer_visible=payload.customer_visible,
        clarification_cycle_id=None,
        auth=auth,
        reason_code=payload.reason_code,
    )
    return {"item": follow_up_item_view(item)}


@router.post("/api/v1/operator/follow-up-items/{follow_up_code}/transition")
def transition_follow_up(
    follow_up_code: str,
    payload: FollowUpTransitionPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    item = session.scalar(select(RequestFollowUpItem).where(RequestFollowUpItem.code == follow_up_code))
    if item is None:
        raise HTTPException(status_code=404, detail="follow_up_not_found")
    service.resolve_follow_up_item(item, target_status=payload.target_status, reason_code=payload.reason_code, auth=auth)
    return {"item": follow_up_item_view(item)}


@router.post("/api/v1/operator/requests/{request_code}/file-links")
def add_request_file_link(
    request_code: str,
    payload: FileLinkPayload,
    auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    service = RequestIntakeService(session)
    try:
        request_record = service.get_request_by_code(request_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    item = service.add_file_link(
        owner_type="request",
        owner_id=request_record.id,
        label=payload.label,
        file_url=payload.file_url,
        visibility=payload.visibility,
        auth=auth,
        reason_code=payload.reason_code,
    )
    return {"item": intake_file_link_view(item)}
