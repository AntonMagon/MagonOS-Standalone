# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit_event
from ..codes import reserve_code
from ..dependencies import get_db, require_roles
from ..models import CommunicationThread, MessageEvent, RequestRecord
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from ..workflow_support import ROLE_CUSTOMER, WorkflowSupportService
from .shared import timeline_event_view

router = APIRouter(tags=["Comms"])


class ThreadCreatePayload(BaseModel):
    owner_type: str
    owner_id: str
    channel: str = Field(min_length=2)
    subject: str = Field(min_length=2)
    last_message_preview: str | None = None
    visibility: str = "internal"


@router.get("/api/v1/operator/comms/threads")
def list_threads(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(select(CommunicationThread).order_by(CommunicationThread.created_at.asc())).all()
    return {"items": [{"id": item.id, "code": item.code, "channel": item.channel, "subject": item.subject, "owner_type": item.owner_type, "owner_id": item.owner_id} for item in items]}


@router.post("/api/v1/operator/comms/threads")
def create_thread(payload: ThreadCreatePayload, auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    item = CommunicationThread(
        code=reserve_code(session, "comms_threads", "COM"),
        owner_type=payload.owner_type,
        owner_id=payload.owner_id,
        channel=payload.channel,
        subject=payload.subject,
        visibility=payload.visibility,
        last_message_preview=payload.last_message_preview,
        created_by_user_id=auth.user_id,
    )
    session.add(item)
    session.flush()
    record_audit_event(session, module_name="comms", action="thread_created", entity_type="comms_thread", entity_id=item.id, entity_code=item.code, auth=auth, reason="manual_thread_create", payload_json={"channel": item.channel})
    return {"item": {"id": item.id, "code": item.code, "subject": item.subject}}


@router.get("/api/v1/operator/comms/notifications")
def list_operator_notifications(
    _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    items = workflow.list_recent_notifications(audience=ROLE_OPERATOR, limit=30)
    return {
        "items": [
            {
                **timeline_event_view(item),
                "reason_display": workflow.reason_display(item.reason_code),
            }
            for item in items
        ]
    }


@router.get("/api/v1/public/requests/{customer_ref}/notifications")
def list_customer_notifications(customer_ref: str, session: Session = Depends(get_db)) -> dict[str, object]:
    workflow = WorkflowSupportService(session)
    request = session.scalar(select(RequestRecord).where(RequestRecord.customer_ref == customer_ref, RequestRecord.deleted_at.is_(None)))
    if request is None:
        raise HTTPException(status_code=404, detail="request_not_found")
    items = [
        item
        for item in workflow.list_timeline(owner_type="request", owner_id=request.id, audience=ROLE_CUSTOMER)
        if item.entry_kind == "notification"
    ]
    return {
        "items": [
            {
                **timeline_event_view(item),
                "reason_display": workflow.reason_display(item.reason_code),
            }
            for item in items
        ]
    }
