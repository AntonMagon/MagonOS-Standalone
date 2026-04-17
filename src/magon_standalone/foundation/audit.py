from __future__ import annotations

from sqlalchemy.orm import Session

from .codes import reserve_code
from .models import AuditEvent
from .security import AuthContext, ROLE_GUEST
from .workflow_support import WorkflowSupportService


def record_audit_event(
    session: Session,
    *,
    module_name: str,
    action: str,
    entity_type: str,
    entity_id: str,
    entity_code: str | None,
    auth: AuthContext | None,
    reason: str | None,
    payload_json: dict | None = None,
    visibility: str = "internal",
    request_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        code=reserve_code(session, "audit_events", "AUD"),
        module_name=module_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_code=entity_code,
        actor_user_id=auth.user_id if auth else None,
        actor_role=auth.role_code if auth else ROLE_GUEST,
        reason=reason,
        visibility=visibility,
        payload_json=payload_json,
        request_id=request_id,
    )
    session.add(event)
    session.flush()
    # RU: audit_event остаётся первичным неизменяемым журналом, а unified timeline/notifications наслаиваются поверх него через message_events.
    WorkflowSupportService(session).emit_message_event_from_audit(event)
    return event
