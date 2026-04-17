# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import record_audit_event
from .codes import reserve_code
from .db import utc_now
from .models import (
    OfferComparisonMetadata,
    OfferConfirmationRecord,
    OfferCriticalChangeResetReason,
    OfferRecord,
    OfferVersion,
    OrderRecord,
    RequestRecord,
)
from .request_intake_services import RequestIntakeService
from .security import AuthContext, ROLE_GUEST
from .workflow_support import WorkflowSupportService

OFFER_CREATION_REQUEST_STATUSES = {"supplier_search", "offer_prep", "offer_sent"}
OFFER_SENDABLE_STATUSES = {"draft", "revised", "declined", "expired"}
OFFER_CONFIRMABLE_STATUSES = {"awaiting_confirmation"}
CONFIRMATION_ACTIONS = {"accept", "decline", "expire"}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _guest_auth() -> AuthContext:
    return AuthContext(user_id=None, role_code=ROLE_GUEST, email=None, full_name=None)


@dataclass(slots=True)
class OfferCurrentBundle:
    offer: OfferRecord
    version: OfferVersion
    comparison: OfferComparisonMetadata | None


class OfferService:
    def __init__(self, session: Session):
        self.session = session
        self.request_service = RequestIntakeService(session)
        self.workflow_support = WorkflowSupportService(session)

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

    def get_offer_by_code(self, offer_code: str) -> OfferRecord:
        item = self.session.scalar(select(OfferRecord).where(OfferRecord.code == offer_code, OfferRecord.deleted_at.is_(None)))
        if item is None:
            raise LookupError("offer_not_found")
        return item

    def list_offers(self) -> list[OfferRecord]:
        return self.session.scalars(select(OfferRecord).where(OfferRecord.deleted_at.is_(None)).order_by(OfferRecord.created_at.asc())).all()

    def list_request_offers(self, request_id: str) -> list[OfferRecord]:
        return self.session.scalars(
            select(OfferRecord)
            .where(OfferRecord.request_id == request_id, OfferRecord.deleted_at.is_(None))
            .order_by(OfferRecord.created_at.asc())
        ).all()

    def get_current_version(self, offer: OfferRecord) -> OfferVersion:
        item = self.session.scalar(
            select(OfferVersion).where(
                OfferVersion.offer_id == offer.id,
                OfferVersion.version_no == offer.current_version_no,
                OfferVersion.deleted_at.is_(None),
            )
        )
        if item is None:
            raise LookupError("offer_version_not_found")
        return item

    def list_versions(self, offer_id: str) -> list[OfferVersion]:
        return self.session.scalars(
            select(OfferVersion)
            .where(OfferVersion.offer_id == offer_id, OfferVersion.deleted_at.is_(None))
            .order_by(OfferVersion.version_no.asc())
        ).all()

    def list_confirmations(self, offer_id: str) -> list[OfferConfirmationRecord]:
        return self.session.scalars(
            select(OfferConfirmationRecord)
            .where(OfferConfirmationRecord.offer_id == offer_id)
            .order_by(OfferConfirmationRecord.occurred_at.asc(), OfferConfirmationRecord.created_at.asc())
        ).all()

    def list_reset_reasons(self, offer_id: str) -> list[OfferCriticalChangeResetReason]:
        return self.session.scalars(
            select(OfferCriticalChangeResetReason)
            .where(OfferCriticalChangeResetReason.offer_id == offer_id)
            .order_by(OfferCriticalChangeResetReason.created_at.asc())
        ).all()

    def get_comparison_metadata(self, offer_version_id: str) -> OfferComparisonMetadata | None:
        return self.session.scalar(
            select(OfferComparisonMetadata).where(OfferComparisonMetadata.offer_version_id == offer_version_id)
        )

    def _create_comparison_metadata(
        self,
        *,
        offer: OfferRecord,
        version: OfferVersion,
        comparison_title: str | None,
        comparison_rank: int | None,
        recommended: bool,
        highlights: list[str] | None,
        metadata: dict | None,
    ) -> OfferComparisonMetadata:
        item = OfferComparisonMetadata(
            code=reserve_code(self.session, "offer_comparison_metadata", "OCM"),
            offer_id=offer.id,
            offer_version_id=version.id,
            comparison_title=_clean_text(comparison_title) or offer.public_summary or offer.code,
            comparison_rank=comparison_rank,
            recommended=recommended,
            highlights_json=highlights or None,
            metadata_json=metadata or None,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def _apply_current_snapshot(self, offer: OfferRecord, version: OfferVersion) -> None:
        offer.current_version_no = version.version_no
        offer.amount = version.amount
        offer.currency_code = version.currency_code
        offer.lead_time_days = version.lead_time_days
        offer.terms_text = version.terms_text
        offer.scenario_type = version.scenario_type
        offer.supplier_ref = version.supplier_ref
        offer.public_summary = version.public_summary
        offer.confirmation_state = version.confirmation_state

    def _create_confirmation_record(
        self,
        *,
        offer: OfferRecord,
        version: OfferVersion,
        action: str,
        confirmation_state: str,
        reason_code: str,
        note: str | None,
        auth: AuthContext | None,
    ) -> OfferConfirmationRecord:
        item = OfferConfirmationRecord(
            code=reserve_code(self.session, "offer_confirmation_records", "OCF"),
            offer_id=offer.id,
            offer_version_id=version.id,
            confirmation_action=action,
            confirmation_state=confirmation_state,
            reason_code=reason_code,
            note=_clean_text(note),
            actor_user_id=auth.user_id if auth else None,
            actor_role=(auth.role_code if auth else ROLE_GUEST),
        )
        self.session.add(item)
        self.session.flush()
        return item

    def _invalidate_previous_confirmation(
        self,
        *,
        offer: OfferRecord,
        previous_version: OfferVersion,
        new_version: OfferVersion,
        reason_code: str,
        note: str | None,
        auth: AuthContext | None,
    ) -> None:
        if previous_version.confirmation_state == "pending":
            return
        reset_reason = OfferCriticalChangeResetReason(
            code=reserve_code(self.session, "offer_critical_change_reset_reasons", "OCR"),
            offer_id=offer.id,
            previous_offer_version_id=previous_version.id,
            new_offer_version_id=new_version.id,
            previous_confirmation_state=previous_version.confirmation_state,
            reason_code=reason_code,
            note=_clean_text(note),
            created_by_user_id=auth.user_id if auth else None,
        )
        self.session.add(reset_reason)
        self.session.flush()
        self._create_confirmation_record(
            offer=offer,
            version=previous_version,
            action="reset_invalidated",
            confirmation_state="reset",
            reason_code=reason_code,
            note=note or "Critical offer revision invalidated previous confirmation.",
            auth=auth,
        )
        record_audit_event(
            self.session,
            module_name="offers",
            action="offer_confirmation_reset",
            entity_type="offer",
            entity_id=offer.id,
            entity_code=offer.code,
            auth=auth,
            reason=reason_code,
            payload_json={
                "previous_version_code": previous_version.code,
                "new_version_code": new_version.code,
                "previous_confirmation_state": previous_version.confirmation_state,
            },
        )

    def create_offer(
        self,
        *,
        request: RequestRecord,
        amount: float | None,
        currency_code: str,
        lead_time_days: int | None,
        terms_text: str | None,
        scenario_type: str,
        supplier_ref: str | None,
        public_summary: str | None,
        comparison_title: str | None,
        comparison_rank: int | None,
        recommended: bool,
        highlights: list[str] | None,
        metadata: dict | None,
        auth: AuthContext | None,
        reason_code: str,
        note: str | None = None,
    ) -> OfferCurrentBundle:
        if request.request_status not in OFFER_CREATION_REQUEST_STATUSES:
            raise HTTPException(status_code=409, detail="request_not_offerable")
        if request.request_status == "supplier_search":
            self.request_service.transition_request(
                request,
                target_status="offer_prep",
                reason_code=reason_code,
                reason_note=note or "Operator moved request into offer preparation.",
                auth=auth,
            )
        offer = OfferRecord(
            code=reserve_code(self.session, "offers", "OFF"),
            request_id=request.id,
            request_ref=request.code,
            current_version_no=1,
            offer_status="draft",
            confirmation_state="pending",
            amount=amount,
            currency_code=currency_code,
            lead_time_days=lead_time_days,
            terms_text=_clean_text(terms_text),
            scenario_type=scenario_type,
            supplier_ref=_clean_text(supplier_ref),
            public_summary=_clean_text(public_summary),
            transition_reason=note or reason_code,
        )
        self.session.add(offer)
        self.session.flush()
        version = OfferVersion(
            code=reserve_code(self.session, "offer_versions", "OFV"),
            offer_id=offer.id,
            version_no=1,
            version_status="draft",
            confirmation_state="pending",
            amount=amount,
            currency_code=currency_code,
            lead_time_days=lead_time_days,
            terms_text=_clean_text(terms_text),
            scenario_type=scenario_type,
            supplier_ref=_clean_text(supplier_ref),
            public_summary=_clean_text(public_summary),
            change_reason_code=reason_code,
            change_note=_clean_text(note),
            is_current=True,
        )
        self.session.add(version)
        self.session.flush()
        comparison = self._create_comparison_metadata(
            offer=offer,
            version=version,
            comparison_title=comparison_title,
            comparison_rank=comparison_rank,
            recommended=recommended,
            highlights=highlights,
            metadata=metadata,
        )
        record_audit_event(
            self.session,
            module_name="offers",
            action="offer_created",
            entity_type="offer",
            entity_id=offer.id,
            entity_code=offer.code,
            auth=auth,
            reason=reason_code,
            payload_json={"request_code": request.code, "version_code": version.code, "scenario_type": scenario_type},
        )
        return OfferCurrentBundle(offer=offer, version=version, comparison=comparison)

    def revise_offer(
        self,
        *,
        offer: OfferRecord,
        amount: float | None,
        currency_code: str,
        lead_time_days: int | None,
        terms_text: str | None,
        scenario_type: str,
        supplier_ref: str | None,
        public_summary: str | None,
        comparison_title: str | None,
        comparison_rank: int | None,
        recommended: bool,
        highlights: list[str] | None,
        metadata: dict | None,
        auth: AuthContext | None,
        reason_code: str,
        note: str | None = None,
    ) -> OfferCurrentBundle:
        request = self.session.scalar(select(RequestRecord).where(RequestRecord.id == offer.request_id))
        if request is None:
            raise HTTPException(status_code=404, detail="request_not_found")
        if request.request_status == "converted_to_order":
            raise HTTPException(status_code=409, detail="offer_already_converted_to_order")
        previous_version = self.get_current_version(offer)
        previous_version.is_current = False
        previous_version.version_status = "superseded"
        new_version = OfferVersion(
            code=reserve_code(self.session, "offer_versions", "OFV"),
            offer_id=offer.id,
            version_no=offer.current_version_no + 1,
            version_status="revised",
            confirmation_state="pending",
            amount=amount,
            currency_code=currency_code,
            lead_time_days=lead_time_days,
            terms_text=_clean_text(terms_text),
            scenario_type=scenario_type,
            supplier_ref=_clean_text(supplier_ref),
            public_summary=_clean_text(public_summary),
            change_reason_code=reason_code,
            change_note=_clean_text(note),
            is_current=True,
        )
        self.session.add(new_version)
        self.session.flush()
        self._invalidate_previous_confirmation(
            offer=offer,
            previous_version=previous_version,
            new_version=new_version,
            reason_code=reason_code,
            note=note,
            auth=auth,
        )
        self._apply_current_snapshot(offer, new_version)
        # RU: Критичная правка оферты обязана явно сбрасывать её в revised, а не возвращать в абстрактный prepared-state.
        offer.offer_status = "revised"
        offer.transition_reason = note or reason_code
        comparison = self._create_comparison_metadata(
            offer=offer,
            version=new_version,
            comparison_title=comparison_title,
            comparison_rank=comparison_rank,
            recommended=recommended,
            highlights=highlights,
            metadata=metadata,
        )
        if request.request_status == "offer_sent":
            self.request_service.transition_request(
                request,
                target_status="offer_prep",
                reason_code=reason_code,
                reason_note=note or "Critical commercial revision requires a new offer send cycle.",
                auth=auth,
            )
        record_audit_event(
            self.session,
            module_name="offers",
            action="offer_version_revised",
            entity_type="offer",
            entity_id=offer.id,
            entity_code=offer.code,
            auth=auth,
            reason=reason_code,
            payload_json={
                "previous_version_code": previous_version.code,
                "new_version_code": new_version.code,
                "new_version_no": new_version.version_no,
            },
        )
        return OfferCurrentBundle(offer=offer, version=new_version, comparison=comparison)

    def send_offer(
        self,
        *,
        offer: OfferRecord,
        auth: AuthContext | None,
        reason_code: str,
        note: str | None = None,
    ) -> OfferCurrentBundle:
        if offer.offer_status not in OFFER_SENDABLE_STATUSES:
            raise HTTPException(status_code=409, detail="offer_not_sendable")
        request = self.session.scalar(select(RequestRecord).where(RequestRecord.id == offer.request_id))
        if request is None:
            raise HTTPException(status_code=404, detail="request_not_found")
        if request.request_status not in {"offer_prep", "offer_sent"}:
            raise HTTPException(status_code=409, detail="request_not_ready_for_offer_send")
        version = self.get_current_version(offer)
        offer.offer_status = "awaiting_confirmation"
        offer.transition_reason = note or reason_code
        version.version_status = "sent"
        if request.request_status != "offer_sent":
            self.request_service.transition_request(
                request,
                target_status="offer_sent",
                reason_code=reason_code,
                reason_note=note or "Commercial offer sent to customer.",
                auth=auth,
            )
        comparison = self.get_comparison_metadata(version.id)
        record_audit_event(
            self.session,
            module_name="offers",
            action="offer_sent",
            entity_type="offer",
            entity_id=offer.id,
            entity_code=offer.code,
            auth=auth,
            reason=reason_code,
            payload_json={"request_code": request.code, "version_code": version.code},
        )
        return OfferCurrentBundle(offer=offer, version=version, comparison=comparison)

    def record_confirmation(
        self,
        *,
        offer: OfferRecord,
        action: str,
        auth: AuthContext | None,
        reason_code: str,
        note: str | None = None,
    ) -> OfferCurrentBundle:
        if action not in CONFIRMATION_ACTIONS:
            raise HTTPException(status_code=422, detail="offer_confirmation_action_invalid")
        if offer.offer_status not in OFFER_CONFIRMABLE_STATUSES:
            raise HTTPException(status_code=409, detail="offer_not_confirmable")
        request = self.session.scalar(select(RequestRecord).where(RequestRecord.id == offer.request_id))
        if request is None:
            raise HTTPException(status_code=404, detail="request_not_found")
        if request.request_status != "offer_sent":
            raise HTTPException(status_code=409, detail="request_not_in_offer_sent")
        version = self.get_current_version(offer)
        if action == "accept":
            confirmation_state = "accepted"
            offer.offer_status = "accepted"
            audit_action = "offer_accepted"
        elif action == "decline":
            confirmation_state = "declined"
            offer.offer_status = "declined"
            audit_action = "offer_declined"
        else:
            confirmation_state = "expired"
            offer.offer_status = "expired"
            audit_action = "offer_expired"
        version.confirmation_state = confirmation_state
        version.version_status = offer.offer_status
        offer.confirmation_state = confirmation_state
        offer.transition_reason = note or reason_code
        self._create_confirmation_record(
            offer=offer,
            version=version,
            action=action,
            confirmation_state=confirmation_state,
            reason_code=reason_code,
            note=note,
            auth=auth,
        )
        comparison = self.get_comparison_metadata(version.id)
        record_audit_event(
            self.session,
            module_name="offers",
            action=audit_action,
            entity_type="offer",
            entity_id=offer.id,
            entity_code=offer.code,
            auth=auth,
            reason=reason_code,
            payload_json={"request_code": request.code, "version_code": version.code, "confirmation_state": confirmation_state},
            visibility="role" if auth and auth.is_authenticated else "customer",
        )
        return OfferCurrentBundle(offer=offer, version=version, comparison=comparison)

    def public_confirm_offer(
        self,
        *,
        customer_ref: str,
        offer_code: str,
        action: str,
        reason_code: str,
        note: str | None = None,
    ) -> OfferCurrentBundle:
        request = self.get_request_by_customer_ref(customer_ref)
        offer = self.get_offer_by_code(offer_code)
        if offer.request_id != request.id:
            raise HTTPException(status_code=404, detail="offer_not_found")
        return self.record_confirmation(
            offer=offer,
            action=action,
            auth=_guest_auth(),
            reason_code=reason_code,
            note=note,
        )

    def convert_to_order(
        self,
        *,
        offer: OfferRecord,
        auth: AuthContext | None,
        reason_code: str,
        note: str | None = None,
    ) -> OrderRecord:
        request = self.session.scalar(select(RequestRecord).where(RequestRecord.id == offer.request_id))
        if request is None:
            raise HTTPException(status_code=404, detail="request_not_found")
        version = self.get_current_version(offer)
        existing = self.session.scalar(
            select(OrderRecord).where(OrderRecord.offer_id == offer.id, OrderRecord.offer_version_id == version.id)
        )
        self.workflow_support.evaluate_offer_to_order(
            offer=offer,
            version=version,
            request=request,
            existing_order=existing is not None,
        ).raise_if_blocked()
        from .order_services import OrderService

        bundle = OrderService(self.session).create_order_from_offer(
            offer=offer,
            version=version,
            request=request,
            auth=auth,
            reason_code=reason_code,
            note=note,
        )
        return bundle.order
