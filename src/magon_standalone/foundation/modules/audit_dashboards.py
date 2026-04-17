# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_container, get_db, require_roles
from ..models import (
    AuditEvent,
    EscalationHint,
    MessageEvent,
    OfferRecord,
    OrderRecord,
    ReasonCodeCatalog,
    RequestReason,
    RequestRecord,
    RuleDefinition,
    RuleVersion,
    SupplierCompany,
    UserAccount,
)
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from ..workflow_support import ROLE_CUSTOMER, WorkflowSupportService, visibility_scopes_for_audience
from .shared import order_public_view, request_operator_view, request_public_view, supplier_operator_view, timeline_event_view

# RU: Этот router собирает operator/admin read-model без обхода workflow-guard слоя и сырых таблиц.
router = APIRouter(tags=["AuditDashboards"])


def _group_counts(session: Session, model, field_name: str) -> dict[str, int]:
    field = getattr(model, field_name)
    rows = session.execute(
        select(field, func.count()).where(model.deleted_at.is_(None)).group_by(field).order_by(field.asc())
    ).all()
    return {str(key): int(count) for key, count in rows}


def _notification_view(item: MessageEvent, workflow: WorkflowSupportService) -> dict[str, object]:
    payload = timeline_event_view(item)
    payload["reason_display"] = workflow.reason_display(item.reason_code)
    return payload


def _dashboard_common(session: Session, workflow: WorkflowSupportService) -> dict[str, object]:
    # RU: Dashboard summary собирается из готовых scoped-срезов, чтобы UI не читал сырые внутренние события напрямую.
    return {
        "requests_by_status": _group_counts(session, RequestRecord, "request_status"),
        "offers_by_status": _group_counts(session, OfferRecord, "offer_status"),
        "orders_by_state": _group_counts(session, OrderRecord, "order_status"),
        "suppliers_by_trust": _group_counts(session, SupplierCompany, "trust_level"),
        "suppliers_by_status": _group_counts(session, SupplierCompany, "supplier_status"),
        "notifications": [_notification_view(item, workflow) for item in workflow.list_recent_notifications(audience=ROLE_OPERATOR, limit=12)],
    }


def _blocked_items(session: Session, workflow: WorkflowSupportService) -> list[dict[str, object]]:
    blocked_requests = session.execute(
        select(RequestReason, RequestRecord)
        .join(RequestRecord, RequestRecord.id == RequestReason.request_id)
        .where(
            RequestReason.deleted_at.is_(None),
            RequestReason.reason_kind == "blocker",
            RequestReason.is_active.is_(True),
            RequestReason.resolved_at.is_(None),
            RequestRecord.deleted_at.is_(None),
        )
        .order_by(RequestReason.created_at.asc())
    ).all()
    items = [
        {
            "kind": "request_blocker",
            "owner_code": request.code,
            "status": request.request_status,
            "reason_code": reason.reason_code,
            "reason_display": workflow.reason_display(reason.reason_code),
            "note": reason.note,
            "created_at": reason.created_at.isoformat(),
        }
        for reason, request in blocked_requests
    ]
    blocked_suppliers = session.scalars(
        select(SupplierCompany)
        .where(
            SupplierCompany.deleted_at.is_(None),
            ((SupplierCompany.blocked_at.is_not(None)) | (SupplierCompany.supplier_status == "blocked")),
        )
        .order_by(SupplierCompany.updated_at.desc())
    ).all()
    items.extend(
        {
            "kind": "supplier_blocked",
            "owner_code": supplier.code,
            "status": supplier.supplier_status,
            "reason_code": supplier.blocked_reason or "supplier_blocked_manual",
            "reason_display": workflow.reason_display(supplier.blocked_reason or "supplier_blocked_manual"),
            "note": supplier.capability_summary,
            "created_at": (supplier.blocked_at or supplier.updated_at).isoformat(),
        }
        for supplier in blocked_suppliers
    )
    return items


def _overdue_items(session: Session, workflow: WorkflowSupportService) -> list[dict[str, object]]:
    hints = session.scalars(select(EscalationHint).where(EscalationHint.enabled.is_(True), EscalationHint.deleted_at.is_(None))).all()
    hint_by_entity = {(item.entity_type, item.status_code): item for item in hints}
    now = func.now()
    del now  # sqlite-safe guard; фактическое now берём ниже через python.
    current_ts = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

    items: list[dict[str, object]] = []
    request_overdue = session.scalars(
        select(RequestRecord)
        .where(
            RequestRecord.deleted_at.is_(None),
            RequestRecord.request_status.not_in(["converted_to_order", "cancelled"]),
            RequestRecord.requested_deadline_at.is_not(None),
            RequestRecord.requested_deadline_at < current_ts,
        )
        .order_by(RequestRecord.requested_deadline_at.asc())
    ).all()
    for request in request_overdue:
        items.append(
            {
                "kind": "request_deadline",
                "owner_code": request.code,
                "status": request.request_status,
                "reason_code": "overdue_request_deadline",
                "reason_display": workflow.reason_display("overdue_request_deadline"),
                "due_at": request.requested_deadline_at.isoformat() if request.requested_deadline_at else None,
                "hint": dict((hint_by_entity.get(("request", request.request_status)) or EscalationHint(metadata_json={})).metadata_json or {}),
            }
        )

    offer_hint = hint_by_entity.get(("offer", "awaiting_confirmation"))
    if offer_hint and offer_hint.overdue_after_minutes:
        threshold = current_ts - timedelta(minutes=int(offer_hint.overdue_after_minutes))
        overdue_offers = session.scalars(
            select(OfferRecord)
            .where(
                OfferRecord.deleted_at.is_(None),
                OfferRecord.offer_status == "awaiting_confirmation",
                OfferRecord.confirmation_state == "pending",
                OfferRecord.updated_at < threshold,
            )
            .order_by(OfferRecord.updated_at.asc())
        ).all()
        items.extend(
            {
                "kind": "offer_confirmation",
                "owner_code": offer.code,
                "request_ref": offer.request_ref,
                "status": offer.offer_status,
                "reason_code": "overdue_offer_confirmation",
                "reason_display": workflow.reason_display("overdue_offer_confirmation"),
                "due_at": offer.updated_at.isoformat(),
                "hint": dict(offer_hint.metadata_json or {}),
            }
            for offer in overdue_offers
        )
    return items


def _resolve_request_by_customer_ref(session: Session, customer_ref: str) -> RequestRecord:
    item = session.scalar(select(RequestRecord).where(RequestRecord.customer_ref == customer_ref, RequestRecord.deleted_at.is_(None)))
    if item is None:
        raise HTTPException(status_code=404, detail="request_not_found")
    return item


@router.get("/api/v1/operator/reason-codes")
def list_reason_codes(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(
        select(ReasonCodeCatalog)
        .where(ReasonCodeCatalog.deleted_at.is_(None))
        .order_by(ReasonCodeCatalog.category.asc(), ReasonCodeCatalog.code.asc())
    ).all()
    return {
        "items": [
            {
                "code": item.code,
                "title": item.title,
                "category": item.category,
                "severity": item.severity,
                "default_visibility_scope": item.default_visibility_scope,
                "description": item.description,
            }
            for item in items
        ]
    }


@router.get("/api/v1/operator/audit/events")
def list_audit_events(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    items = session.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc())).all()
    return {
        "items": [
            {
                "code": item.code,
                "module_name": item.module_name,
                "action": item.action,
                "entity_type": item.entity_type,
                "entity_code": item.entity_code,
                "actor_role": item.actor_role,
                "reason": item.reason,
                "reason_display": workflow.reason_display(item.reason),
                "visibility_scope": item.visibility,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ]
    }


@router.get("/api/v1/operator/timeline/{owner_type}/{owner_code}")
def operator_timeline(
    owner_type: str,
    owner_code: str,
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    try:
        owner_id = workflow.resolve_owner_id(owner_type, owner_code)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    items = workflow.list_timeline(owner_type=owner_type, owner_id=owner_id, audience=ROLE_OPERATOR)
    return {"items": [_notification_view(item, workflow) for item in items]}


@router.get("/api/v1/public/requests/{customer_ref}/dashboard")
def customer_dashboard(customer_ref: str, session: Session = Depends(get_db)) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    request = _resolve_request_by_customer_ref(session, customer_ref)
    timeline = workflow.list_timeline(owner_type="request", owner_id=request.id, audience=ROLE_CUSTOMER)
    notifications = [item for item in timeline if item.entry_kind == "notification"]
    order = session.scalar(select(OrderRecord).where(OrderRecord.request_id == request.id, OrderRecord.deleted_at.is_(None)).order_by(OrderRecord.created_at.desc()))
    offers = session.scalars(select(OfferRecord).where(OfferRecord.request_id == request.id, OfferRecord.deleted_at.is_(None)).order_by(OfferRecord.created_at.desc())).all()
    return {
        "request": request_public_view(request),
        "order": order_public_view(order) if order else None,
        "notifications": [_notification_view(item, workflow) for item in notifications],
        "timeline": [_notification_view(item, workflow) for item in timeline],
        "offers_pending_confirmation": sum(1 for item in offers if item.offer_status == "awaiting_confirmation" and item.confirmation_state == "pending"),
        "documents_waiting_confirmation": session.scalar(
            select(func.count())
            .select_from(MessageEvent)
            .where(
                MessageEvent.owner_type == "request",
                MessageEvent.owner_id == request.id,
                MessageEvent.entry_kind == "notification",
                MessageEvent.visibility_scope.in_(visibility_scopes_for_audience(ROLE_CUSTOMER)),
                MessageEvent.event_type == "document_sent",
                MessageEvent.deleted_at.is_(None),
            )
        )
        or 0,
    }


@router.get("/api/v1/operator/workbench")
def operator_workbench(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    return {
        **_dashboard_common(session, workflow),
        "blocked_items": _blocked_items(session, workflow),
        "overdue_items": _overdue_items(session, workflow),
        "offers_pending_confirmation": [
            {
                "code": item.code,
                "request_ref": item.request_ref,
                "offer_status": item.offer_status,
                "confirmation_state": item.confirmation_state,
                "updated_at": item.updated_at.isoformat(),
            }
            for item in session.scalars(
                select(OfferRecord)
                .where(OfferRecord.deleted_at.is_(None), OfferRecord.offer_status == "awaiting_confirmation", OfferRecord.confirmation_state == "pending")
                .order_by(OfferRecord.updated_at.asc())
            ).all()
        ],
    }


@router.get("/api/v1/admin/dashboard")
def admin_dashboard(
    _: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
    container=Depends(get_container),
) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    return {
        **_dashboard_common(session, workflow),
        "blocked_items": _blocked_items(session, workflow),
        "overdue_items": _overdue_items(session, workflow),
        "counts": {
            "users": int(session.scalar(select(func.count()).select_from(UserAccount)) or 0),
            "rules": int(session.scalar(select(func.count()).select_from(RuleDefinition)) or 0),
            "rule_versions": int(session.scalar(select(func.count()).select_from(RuleVersion)) or 0),
            "message_events": int(session.scalar(select(func.count()).select_from(MessageEvent)) or 0),
            "notifications": int(session.scalar(select(func.count()).select_from(MessageEvent).where(MessageEvent.entry_kind == "notification")) or 0),
        },
        "telemetry": container.telemetry.snapshot(),
    }


@router.get("/api/v1/operator/dashboard/supply")
def supply_dashboard(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    blocked_suppliers = [
        {
            "code": item.code,
            "display_name": item.display_name,
            "trust_level": item.trust_level,
            "supplier_status": item.supplier_status,
            "blocked_reason": item.blocked_reason,
            "reason_display": workflow.reason_display(item.blocked_reason or "supplier_blocked_manual"),
        }
        for item in session.scalars(
            select(SupplierCompany)
            .where(SupplierCompany.deleted_at.is_(None))
            .order_by(SupplierCompany.updated_at.desc())
        ).all()
        if item.blocked_at is not None or item.supplier_status == "blocked"
    ]
    return {
        "suppliers_by_trust": _group_counts(session, SupplierCompany, "trust_level"),
        "suppliers_by_status": _group_counts(session, SupplierCompany, "supplier_status"),
        "blocked_suppliers": blocked_suppliers,
        "top_suppliers": [
            supplier_operator_view(item)
            for item in session.scalars(
                select(SupplierCompany)
                .where(SupplierCompany.deleted_at.is_(None))
                .order_by(SupplierCompany.updated_at.desc())
                .limit(12)
            ).all()
        ],
    }


@router.get("/api/v1/operator/dashboard/processing")
def processing_dashboard(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    return {
        "requests_by_status": _group_counts(session, RequestRecord, "request_status"),
        "orders_by_state": _group_counts(session, OrderRecord, "order_status"),
        "offers_pending_confirmation": [
            {
                "code": item.code,
                "request_ref": item.request_ref,
                "confirmation_state": item.confirmation_state,
                "updated_at": item.updated_at.isoformat(),
            }
            for item in session.scalars(
                select(OfferRecord)
                .where(OfferRecord.deleted_at.is_(None), OfferRecord.offer_status == "awaiting_confirmation", OfferRecord.confirmation_state == "pending")
                .order_by(OfferRecord.updated_at.asc())
            ).all()
        ],
        "blocked_items": _blocked_items(session, workflow),
        "overdue_items": _overdue_items(session, workflow),
    }


@router.get("/api/v1/operator/dashboard/summary")
def dashboard_summary(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
    container=Depends(get_container),
) -> dict[str, object]:
    workflow = WorkflowSupportService(session)

    def _count(model) -> int:
        return int(session.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "service": container.settings.app_name,
        "env": container.settings.env_name,
        "counts": {
            "users": _count(UserAccount),
            "suppliers": _count(SupplierCompany),
            "requests": _count(RequestRecord),
            "offers": _count(OfferRecord),
            "orders": _count(OrderRecord),
            "audit_events": _count(AuditEvent),
            "message_events": _count(MessageEvent),
        },
        "processing": {
            "blocked_items": len(_blocked_items(session, workflow)),
            "overdue_items": len(_overdue_items(session, workflow)),
        },
        "telemetry": container.telemetry.snapshot(),
    }
