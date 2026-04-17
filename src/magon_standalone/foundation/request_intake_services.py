from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .audit import record_audit_event
from .codes import reserve_code
from .db import utc_now
from .models import (
    AuditEvent,
    CatalogItem,
    DraftRequest,
    IntakeFileLink,
    RequestClarificationCycle,
    RequestFollowUpItem,
    RequestReason,
    RequestRecord,
    RequiredFieldState,
    UserAccount,
)
from .security import AuthContext, ROLE_GUEST
from .workflow_support import WorkflowSupportService

DRAFT_STATUSES = {"draft", "awaiting_data", "ready_to_submit", "blocked", "abandoned", "archived"}
REQUEST_STATUSES = {
    "new",
    "needs_review",
    "needs_clarification",
    "supplier_search",
    "offer_prep",
    "offer_sent",
    "converted_to_order",
    "cancelled",
}
FOLLOW_UP_STATUSES = {"open", "waiting_customer", "resolved", "cancelled"}
REASON_KINDS = {"reason", "blocker"}
DRAFT_STALE_AFTER = timedelta(days=7)

DRAFT_REQUIRED_FIELDS = {
    "customer_email": "Контактный email обязателен для перевода в Request.",
    "title": "Нужно короткое название запроса.",
    "summary": "Нужно описание задачи и объёма.",
    "item_service_context": "Нужен контекст товара или услуги.",
    "city": "Нужно указать город или точку доставки.",
    "requested_deadline_at": "Нужен запрошенный дедлайн.",
}

REQUEST_TRANSITIONS: dict[str, set[str]] = {
    "new": {"needs_review", "cancelled"},
    "needs_review": {"needs_clarification", "supplier_search", "cancelled"},
    "needs_clarification": {"needs_review", "supplier_search", "cancelled"},
    "supplier_search": {"needs_clarification", "offer_prep", "cancelled"},
    "offer_prep": {"needs_clarification", "offer_sent", "cancelled"},
    "offer_sent": {"needs_clarification", "offer_prep", "converted_to_order", "cancelled"},
    "converted_to_order": set(),
    "cancelled": set(),
}


@dataclass(slots=True)
class DraftRequirementSnapshot:
    overall_status: str
    missing_fields: list[str]
    ready_to_submit: bool


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _stringify_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return str(value)
    return str(value)


def _coerce_aware_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        # RU: SQLite в local/test может вернуть naive datetime, поэтому
        # intake-guards приводят её к UTC, чтобы не ломать transition checks.
        return value.replace(tzinfo=timezone.utc)
    return value


def _guest_auth() -> AuthContext:
    return AuthContext(user_id=None, role_code=ROLE_GUEST, email=None, full_name=None)


class RequestIntakeService:
    def __init__(self, session: Session):
        self.session = session
        self.workflow_support = WorkflowSupportService(session)

    def get_catalog_item_by_code(self, item_code: str | None) -> CatalogItem | None:
        if not item_code:
            return None
        return self.session.scalar(select(CatalogItem).where(CatalogItem.code == item_code, CatalogItem.deleted_at.is_(None)))

    def get_draft_by_code(self, draft_code: str) -> DraftRequest:
        item = self.session.scalar(select(DraftRequest).where(DraftRequest.code == draft_code))
        if item is None:
            raise LookupError("draft_not_found")
        self.mark_draft_abandoned_if_stale(item)
        return item

    def get_request_by_code(self, request_code: str) -> RequestRecord:
        item = self.session.scalar(select(RequestRecord).where(RequestRecord.code == request_code))
        if item is None:
            raise LookupError("request_not_found")
        return item

    def get_request_by_customer_ref(self, customer_ref: str) -> RequestRecord:
        item = self.session.scalar(select(RequestRecord).where(RequestRecord.customer_ref == customer_ref))
        if item is None:
            raise LookupError("request_not_found")
        return item

    def list_drafts(self) -> list[DraftRequest]:
        items = self.session.scalars(select(DraftRequest).order_by(DraftRequest.created_at.asc())).all()
        for item in items:
            self.mark_draft_abandoned_if_stale(item)
        return items

    def list_requests(self) -> list[RequestRecord]:
        return self.session.scalars(select(RequestRecord).order_by(RequestRecord.created_at.asc())).all()

    def list_required_fields(self, owner_type: str, owner_id: str) -> list[RequiredFieldState]:
        return self.session.scalars(
            select(RequiredFieldState)
            .where(RequiredFieldState.owner_type == owner_type, RequiredFieldState.owner_id == owner_id)
            .order_by(RequiredFieldState.field_name.asc())
        ).all()

    def list_file_links(self, owner_type: str, owner_id: str) -> list[IntakeFileLink]:
        return self.session.scalars(
            select(IntakeFileLink)
            .where(IntakeFileLink.owner_type == owner_type, IntakeFileLink.owner_id == owner_id, IntakeFileLink.deleted_at.is_(None))
            .order_by(IntakeFileLink.created_at.asc())
        ).all()

    def list_request_reasons(self, request_id: str) -> list[RequestReason]:
        return self.session.scalars(
            select(RequestReason)
            .where(RequestReason.request_id == request_id, RequestReason.deleted_at.is_(None))
            .order_by(RequestReason.created_at.asc())
        ).all()

    def list_clarification_cycles(self, request_id: str) -> list[RequestClarificationCycle]:
        return self.session.scalars(
            select(RequestClarificationCycle)
            .where(RequestClarificationCycle.request_id == request_id, RequestClarificationCycle.deleted_at.is_(None))
            .order_by(RequestClarificationCycle.cycle_index.asc())
        ).all()

    def list_follow_up_items(self, request_id: str) -> list[RequestFollowUpItem]:
        return self.session.scalars(
            select(RequestFollowUpItem)
            .where(RequestFollowUpItem.request_id == request_id, RequestFollowUpItem.deleted_at.is_(None))
            .order_by(RequestFollowUpItem.created_at.asc())
        ).all()

    def list_timeline_events(self, *, entity_type: str, entity_id: str) -> list[AuditEvent]:
        return self.session.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_type == entity_type, AuditEvent.entity_id == entity_id)
            .order_by(AuditEvent.created_at.asc())
        ).all()

    def mark_draft_abandoned_if_stale(self, draft: DraftRequest) -> DraftRequest:
        if draft.draft_status in {"archived", "blocked", "abandoned"}:
            return draft
        reference = _coerce_aware_datetime(
            draft.last_customer_activity_at or draft.last_autosaved_at or draft.updated_at or draft.created_at
        )
        if reference and utc_now() - reference >= DRAFT_STALE_AFTER:
            draft.draft_status = "abandoned"
            draft.abandoned_at = utc_now()
            draft.public_status = "abandoned"
            draft.internal_status = "abandoned"
            draft.last_transition_reason_code = draft.last_transition_reason_code or "draft_stale_timeout"
            draft.last_transition_note = draft.last_transition_note or "Draft marked abandoned after inactivity timeout."
        return draft

    def _apply_catalog_context(self, draft: DraftRequest) -> None:
        if draft.catalog_item_id and not _clean_text(draft.item_service_context):
            item = self.session.scalar(select(CatalogItem).where(CatalogItem.id == draft.catalog_item_id))
            if item is not None:
                draft.item_service_context = item.public_title
        if not _clean_text(draft.source_channel):
            draft.source_channel = draft.intake_channel or "web_public"

    def sync_required_fields(self, draft: DraftRequest) -> DraftRequirementSnapshot:
        self._apply_catalog_context(draft)
        states_by_field = {
            item.field_name: item
            for item in self.list_required_fields("draft_request", draft.id)
        }
        missing_fields: list[str] = []
        present_count = 0
        for field_name, message in DRAFT_REQUIRED_FIELDS.items():
            value = getattr(draft, field_name, None)
            if field_name == "requested_deadline_at":
                is_present = value is not None
            else:
                is_present = _clean_text(value) is not None
            if is_present:
                present_count += 1
            item = states_by_field.get(field_name)
            if item is None:
                item = RequiredFieldState(
                    code=reserve_code(self.session, "required_fields_state", "RFS"),
                    owner_type="draft_request",
                    owner_id=draft.id,
                    field_name=field_name,
                    is_required=True,
                )
                self.session.add(item)
                states_by_field[field_name] = item
            item.field_status = "present" if is_present else "missing"
            item.message = None if is_present else message
            item.current_value = _stringify_value(value)
            item.last_checked_at = utc_now()
            if not is_present:
                missing_fields.append(field_name)

        if draft.draft_status == "blocked":
            overall_status = "blocked"
        elif draft.archived_at or draft.submitted_request_id:
            overall_status = "archived"
        elif draft.abandoned_at:
            overall_status = "abandoned"
        elif not present_count:
            overall_status = "draft"
        elif missing_fields:
            overall_status = "awaiting_data"
        else:
            overall_status = "ready_to_submit"

        draft.draft_status = overall_status
        draft.public_status = overall_status
        draft.internal_status = overall_status
        return DraftRequirementSnapshot(
            overall_status=overall_status,
            missing_fields=missing_fields,
            ready_to_submit=overall_status == "ready_to_submit",
        )

    def create_draft(
        self,
        *,
        customer_email: str | None,
        customer_name: str | None,
        customer_phone: str | None,
        guest_company_name: str | None,
        company_id: str | None,
        catalog_item_id: str | None,
        title: str | None,
        summary: str | None,
        item_service_context: str | None,
        city: str | None,
        geo_json: dict | None,
        source_channel: str,
        intake_channel: str,
        locale_code: str,
        requested_deadline_at: datetime | None,
        auth: AuthContext | None,
        reason_code: str,
        reason_note: str | None = None,
    ) -> DraftRequest:
        now = utc_now()
        draft = DraftRequest(
            code=reserve_code(self.session, "draft_requests", "DRF"),
            company_id=company_id,
            catalog_item_id=catalog_item_id,
            customer_email=_clean_text(customer_email),
            customer_name=_clean_text(customer_name),
            customer_phone=_clean_text(customer_phone),
            guest_company_name=_clean_text(guest_company_name),
            title=_clean_text(title),
            summary=_clean_text(summary),
            item_service_context=_clean_text(item_service_context),
            city=_clean_text(city),
            geo_json=geo_json or None,
            source_channel=source_channel,
            intake_channel=intake_channel,
            locale_code=locale_code,
            requested_deadline_at=requested_deadline_at,
            requested_due_at=requested_deadline_at,
            last_customer_activity_at=now,
            last_autosaved_at=now,
            last_transition_reason_code=reason_code,
            last_transition_note=reason_note,
            last_transition_reason=reason_note or reason_code,
        )
        self.session.add(draft)
        self.session.flush()
        snapshot = self.sync_required_fields(draft)
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="draft_created",
            entity_type="draft_request",
            entity_id=draft.id,
            entity_code=draft.code,
            auth=auth,
            reason=reason_code,
            payload_json={
                "draft_status": snapshot.overall_status,
                "source_channel": draft.source_channel,
                "catalog_item_id": draft.catalog_item_id,
            },
            visibility="role" if auth and auth.is_authenticated else "role",
        )
        return draft

    def update_draft(
        self,
        draft: DraftRequest,
        *,
        title: str | None,
        summary: str | None,
        customer_name: str | None,
        customer_email: str | None,
        customer_phone: str | None,
        guest_company_name: str | None,
        item_service_context: str | None,
        city: str | None,
        geo_json: dict | None,
        requested_deadline_at: datetime | None,
        locale_code: str | None,
        source_channel: str | None,
        auth: AuthContext | None,
        reason_code: str,
        reason_note: str | None = None,
    ) -> DraftRequirementSnapshot:
        if draft.draft_status in {"archived", "abandoned"} and draft.submitted_request_id:
            raise HTTPException(status_code=409, detail="draft_not_editable")
        draft.title = _clean_text(title)
        draft.summary = _clean_text(summary)
        draft.customer_name = _clean_text(customer_name)
        draft.customer_email = _clean_text(customer_email)
        draft.customer_phone = _clean_text(customer_phone)
        draft.guest_company_name = _clean_text(guest_company_name)
        draft.item_service_context = _clean_text(item_service_context)
        draft.city = _clean_text(city)
        draft.geo_json = geo_json or None
        draft.requested_deadline_at = requested_deadline_at
        draft.requested_due_at = requested_deadline_at
        if locale_code:
            draft.locale_code = locale_code
        if source_channel:
            draft.source_channel = source_channel
            draft.intake_channel = source_channel
        draft.last_autosaved_at = utc_now()
        draft.last_customer_activity_at = utc_now()
        draft.abandoned_at = None
        draft.last_transition_reason_code = reason_code
        draft.last_transition_note = reason_note
        draft.last_transition_reason = reason_note or reason_code
        snapshot = self.sync_required_fields(draft)
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="draft_autosaved",
            entity_type="draft_request",
            entity_id=draft.id,
            entity_code=draft.code,
            auth=auth,
            reason=reason_code,
            payload_json={"draft_status": snapshot.overall_status, "missing_fields": snapshot.missing_fields},
            visibility="role",
        )
        return snapshot

    def set_draft_status(
        self,
        draft: DraftRequest,
        *,
        target_status: str,
        auth: AuthContext | None,
        reason_code: str,
        reason_note: str | None = None,
    ) -> DraftRequest:
        if target_status not in DRAFT_STATUSES:
            raise HTTPException(status_code=422, detail="draft_status_invalid")
        draft.draft_status = target_status
        draft.public_status = target_status
        draft.internal_status = target_status
        draft.last_transition_reason_code = reason_code
        draft.last_transition_note = reason_note
        draft.last_transition_reason = reason_note or reason_code
        if target_status == "abandoned":
            draft.abandoned_at = utc_now()
        if target_status == "archived":
            draft.archived_at = draft.archived_at or utc_now()
            draft.archived_reason = reason_code
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="draft_status_changed",
            entity_type="draft_request",
            entity_id=draft.id,
            entity_code=draft.code,
            auth=auth,
            reason=reason_code,
            payload_json={"target_status": target_status, "note": reason_note},
        )
        return draft

    def add_file_link(
        self,
        *,
        owner_type: str,
        owner_id: str,
        label: str,
        file_url: str,
        visibility: str,
        auth: AuthContext | None,
        reason_code: str,
    ) -> IntakeFileLink:
        item = IntakeFileLink(
            code=reserve_code(self.session, "intake_file_links", "LNK"),
            owner_type=owner_type,
            owner_id=owner_id,
            label=label.strip(),
            file_url=file_url.strip(),
            file_kind="external_link",
            visibility=visibility,
            created_by_user_id=auth.user_id if auth else None,
        )
        self.session.add(item)
        self.session.flush()
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="file_link_added",
            entity_type=owner_type,
            entity_id=owner_id,
            entity_code=None,
            auth=auth,
            reason=reason_code,
            payload_json={"label": item.label, "file_url": item.file_url, "visibility": visibility},
            visibility="role",
        )
        return item

    def _ensure_request_customer_ref(self) -> str:
        return reserve_code(self.session, "request_customer_refs", "CRF")

    def submit_draft(
        self,
        draft: DraftRequest,
        *,
        auth: AuthContext | None,
        reason_code: str,
        reason_note: str | None = None,
    ) -> RequestRecord:
        self.mark_draft_abandoned_if_stale(draft)
        snapshot = self.sync_required_fields(draft)
        if draft.submitted_request_id:
            raise HTTPException(status_code=409, detail="draft_already_submitted")
        if draft.draft_status == "blocked":
            raise HTTPException(status_code=409, detail="draft_blocked")
        self.workflow_support.evaluate_draft_submit(
            draft=draft,
            snapshot=snapshot,
            file_links=self.list_file_links("draft_request", draft.id),
        ).raise_if_blocked()

        request_record = RequestRecord(
            code=reserve_code(self.session, "requests", "REQ"),
            customer_ref=self._ensure_request_customer_ref(),
            draft_request_id=draft.id,
            company_id=draft.company_id,
            catalog_item_id=draft.catalog_item_id,
            customer_email=draft.customer_email,
            customer_name=draft.customer_name,
            customer_phone=draft.customer_phone,
            guest_company_name=draft.guest_company_name,
            title=draft.title,
            summary=draft.summary,
            item_service_context=draft.item_service_context,
            source_channel=draft.source_channel,
            city=draft.city,
            geo_json=draft.geo_json,
            request_status="new",
            locale_code=draft.locale_code,
            requested_due_at=draft.requested_deadline_at,
            requested_deadline_at=draft.requested_deadline_at,
            owner_user_id=auth.user_id if auth and auth.role_code in {"operator", "admin"} else None,
            intake_reason=reason_note or reason_code,
            last_transition_reason_code=reason_code,
            last_transition_note=reason_note,
        )
        self.session.add(request_record)
        self.session.flush()

        draft.submitted_request_id = request_record.id
        draft.submitted_at = utc_now()
        draft.archived_at = utc_now()
        draft.archived_reason = "submitted_to_request"
        draft.draft_status = "archived"
        draft.public_status = "archived"
        draft.internal_status = "archived"
        draft.last_transition_reason_code = reason_code
        draft.last_transition_note = reason_note
        draft.last_transition_reason = reason_note or reason_code

        self.add_request_reason(
            request=request_record,
            reason_kind="reason",
            reason_code=reason_code,
            note=reason_note or "Draft submitted into central request intake.",
            auth=auth,
            record_audit=False,
        )

        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="draft_submitted",
            entity_type="draft_request",
            entity_id=draft.id,
            entity_code=draft.code,
            auth=auth,
            reason=reason_code,
            payload_json={"request_code": request_record.code, "customer_ref": request_record.customer_ref},
        )
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="request_created",
            entity_type="request",
            entity_id=request_record.id,
            entity_code=request_record.code,
            auth=auth,
            reason=reason_code,
            payload_json={"draft_code": draft.code, "customer_ref": request_record.customer_ref},
        )
        return request_record

    def add_request_reason(
        self,
        *,
        request: RequestRecord,
        reason_kind: str,
        reason_code: str,
        note: str | None,
        auth: AuthContext | None,
        record_audit: bool = True,
    ) -> RequestReason:
        if reason_kind not in REASON_KINDS:
            raise HTTPException(status_code=422, detail="request_reason_kind_invalid")
        item = RequestReason(
            code=reserve_code(self.session, "request_reasons", "RSN"),
            request_id=request.id,
            reason_kind=reason_kind,
            reason_code=reason_code,
            note=note,
            is_active=True,
            created_by_user_id=auth.user_id if auth else None,
        )
        self.session.add(item)
        self.session.flush()
        if record_audit:
            record_audit_event(
                self.session,
                module_name="drafts_requests",
                action="request_reason_added",
                entity_type="request",
                entity_id=request.id,
                entity_code=request.code,
                auth=auth,
                reason=reason_code,
                payload_json={"reason_kind": reason_kind, "note": note},
            )
        return item

    def open_clarification_cycle(
        self,
        request: RequestRecord,
        *,
        reason_code: str,
        note: str | None,
        auth: AuthContext | None,
    ) -> RequestClarificationCycle:
        active = self.session.scalar(
            select(RequestClarificationCycle).where(
                RequestClarificationCycle.request_id == request.id,
                RequestClarificationCycle.cycle_status == "open",
                RequestClarificationCycle.deleted_at.is_(None),
            )
        )
        if active is not None:
            return active
        next_index = int(
            self.session.scalar(
                select(func.coalesce(func.max(RequestClarificationCycle.cycle_index), 0)).where(
                    RequestClarificationCycle.request_id == request.id
                )
            )
            or 0
        ) + 1
        cycle = RequestClarificationCycle(
            code=reserve_code(self.session, "request_clarification_cycles", "CLC"),
            request_id=request.id,
            cycle_index=next_index,
            cycle_status="open",
            opened_reason_code=reason_code,
            opened_note=note,
            opened_by_user_id=auth.user_id if auth else None,
        )
        self.session.add(cycle)
        self.session.flush()
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="clarification_cycle_opened",
            entity_type="request",
            entity_id=request.id,
            entity_code=request.code,
            auth=auth,
            reason=reason_code,
            payload_json={"cycle_code": cycle.code, "cycle_index": cycle.cycle_index},
        )
        return cycle

    def close_open_clarification_cycles(self, request: RequestRecord, *, auth: AuthContext | None, reason_code: str) -> None:
        cycles = self.session.scalars(
            select(RequestClarificationCycle).where(
                RequestClarificationCycle.request_id == request.id,
                RequestClarificationCycle.cycle_status == "open",
                RequestClarificationCycle.deleted_at.is_(None),
            )
        ).all()
        now = utc_now()
        for cycle in cycles:
            cycle.cycle_status = "closed"
            cycle.closed_by_user_id = auth.user_id if auth else None
            cycle.closed_at = now
        if cycles:
            record_audit_event(
                self.session,
                module_name="drafts_requests",
                action="clarification_cycles_closed",
                entity_type="request",
                entity_id=request.id,
                entity_code=request.code,
                auth=auth,
                reason=reason_code,
                payload_json={"count": len(cycles)},
            )

    def add_follow_up_item(
        self,
        *,
        request: RequestRecord,
        title: str,
        detail: str | None,
        due_at: datetime | None,
        owner_user_id: str | None,
        customer_visible: bool,
        clarification_cycle_id: str | None,
        auth: AuthContext | None,
        reason_code: str,
    ) -> RequestFollowUpItem:
        item = RequestFollowUpItem(
            code=reserve_code(self.session, "request_follow_up_items", "FLW"),
            request_id=request.id,
            clarification_cycle_id=clarification_cycle_id,
            title=title.strip(),
            detail=_clean_text(detail),
            follow_up_status="waiting_customer" if customer_visible else "open",
            owner_user_id=owner_user_id,
            due_at=due_at,
            customer_visible=customer_visible,
        )
        self.session.add(item)
        self.session.flush()
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="follow_up_item_created",
            entity_type="request",
            entity_id=request.id,
            entity_code=request.code,
            auth=auth,
            reason=reason_code,
            payload_json={"follow_up_code": item.code, "customer_visible": customer_visible},
        )
        return item

    def resolve_request_reason(
        self,
        item: RequestReason,
        *,
        reason_code: str,
        auth: AuthContext | None,
    ) -> RequestReason:
        item.is_active = False
        item.resolved_at = utc_now()
        item.resolved_by_user_id = auth.user_id if auth else None
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="request_reason_resolved",
            entity_type="request",
            entity_id=item.request_id,
            entity_code=None,
            auth=auth,
            reason=reason_code,
            payload_json={"request_reason_code": item.code, "resolved_reason_code": item.reason_code},
        )
        return item

    def transition_request(
        self,
        request: RequestRecord,
        *,
        target_status: str,
        reason_code: str,
        reason_note: str | None,
        auth: AuthContext | None,
        owner_user_id: str | None = None,
        assignee_user_id: str | None = None,
    ) -> RequestRecord:
        if target_status not in REQUEST_STATUSES:
            raise HTTPException(status_code=422, detail="request_status_invalid")
        allowed_targets = REQUEST_TRANSITIONS.get(request.request_status, set())
        if target_status not in allowed_targets:
            self.workflow_support.evaluate_request_transition(
                request=request,
                target_status=target_status,
                allowed_targets=allowed_targets,
                active_blockers=[],
            ).raise_if_blocked()
        active_blockers = [
            item
            for item in self.list_request_reasons(request.id)
            if item.reason_kind == "blocker" and item.is_active and item.resolved_at is None
        ]
        self.workflow_support.evaluate_request_transition(
            request=request,
            target_status=target_status,
            allowed_targets=allowed_targets,
            active_blockers=active_blockers,
        ).raise_if_blocked()
        if owner_user_id is not None:
            request.owner_user_id = owner_user_id
        elif request.owner_user_id is None and auth and auth.user_id:
            request.owner_user_id = auth.user_id
        if assignee_user_id is not None:
            request.assignee_user_id = assignee_user_id
        request.request_status = target_status
        request.last_transition_reason_code = reason_code
        request.last_transition_note = reason_note
        if target_status == "needs_clarification":
            self.open_clarification_cycle(request, reason_code=reason_code, note=reason_note, auth=auth)
        else:
            self.close_open_clarification_cycles(request, auth=auth, reason_code=reason_code)
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="request_status_changed",
            entity_type="request",
            entity_id=request.id,
            entity_code=request.code,
            auth=auth,
            reason=reason_code,
            payload_json={
                "target_status": target_status,
                "owner_user_id": request.owner_user_id,
                "assignee_user_id": request.assignee_user_id,
                "note": reason_note,
            },
        )
        return request

    def resolve_follow_up_item(
        self,
        item: RequestFollowUpItem,
        *,
        target_status: str,
        reason_code: str,
        auth: AuthContext | None,
    ) -> RequestFollowUpItem:
        if target_status not in FOLLOW_UP_STATUSES:
            raise HTTPException(status_code=422, detail="follow_up_status_invalid")
        item.follow_up_status = target_status
        if target_status in {"resolved", "cancelled"}:
            item.closed_at = utc_now()
            item.closed_reason_code = reason_code
        record_audit_event(
            self.session,
            module_name="drafts_requests",
            action="follow_up_item_updated",
            entity_type="request",
            entity_id=item.request_id,
            entity_code=None,
            auth=auth,
            reason=reason_code,
            payload_json={"follow_up_code": item.code, "target_status": target_status},
        )
        return item

    def get_user_by_code(self, user_code: str | None) -> UserAccount | None:
        if not user_code:
            return None
        return self.session.scalar(select(UserAccount).where(UserAccount.code == user_code, UserAccount.deleted_at.is_(None)))
