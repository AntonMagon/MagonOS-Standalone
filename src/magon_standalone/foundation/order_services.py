from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import record_audit_event
from .codes import reserve_code
from .db import utc_now
from .models import InternalLedgerEntry, OfferRecord, OfferVersion, OrderLine, OrderRecord, PaymentRecord, RequestRecord
from .request_intake_services import RequestIntakeService
from .security import AuthContext
from .workflow_support import WorkflowSupportService

ORDER_ACTIONS = {
    "assign_supplier",
    "confirm_start",
    "mark_production",
    "ready",
    "delivery",
    "complete",
    "cancel",
    "dispute",
}
PAYMENT_STATES = {"created", "pending", "confirmed", "failed", "partially_refunded", "refunded"}
ORDER_PAYMENT_TRANSITIONS = {
    "created": {"pending", "confirmed", "failed"},
    "pending": {"confirmed", "failed", "partially_refunded", "refunded"},
    "confirmed": {"partially_refunded", "refunded"},
    "failed": {"pending"},
    "partially_refunded": {"refunded"},
    "refunded": set(),
}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


@dataclass(slots=True)
class OrderBundle:
    order: OrderRecord
    lines: list[OrderLine]
    payments: list[PaymentRecord]
    ledger: list[InternalLedgerEntry]


class OrderService:
    def __init__(self, session: Session):
        self.session = session
        self.request_service = RequestIntakeService(session)
        self.workflow_support = WorkflowSupportService(session)

    def get_order_by_code(self, order_code: str) -> OrderRecord:
        item = self.session.scalar(select(OrderRecord).where(OrderRecord.code == order_code, OrderRecord.deleted_at.is_(None)))
        if item is None:
            raise LookupError("order_not_found")
        return item

    def list_orders(self) -> list[OrderRecord]:
        return self.session.scalars(select(OrderRecord).where(OrderRecord.deleted_at.is_(None)).order_by(OrderRecord.created_at.asc())).all()

    def list_request_orders(self, request_id: str) -> list[OrderRecord]:
        return self.session.scalars(
            select(OrderRecord).where(OrderRecord.request_id == request_id, OrderRecord.deleted_at.is_(None)).order_by(OrderRecord.created_at.asc())
        ).all()

    def list_order_lines(self, order_id: str) -> list[OrderLine]:
        return self.session.scalars(
            select(OrderLine).where(OrderLine.order_id == order_id, OrderLine.deleted_at.is_(None)).order_by(OrderLine.created_at.asc())
        ).all()

    def list_payment_records(self, order_id: str) -> list[PaymentRecord]:
        return self.session.scalars(
            select(PaymentRecord).where(PaymentRecord.order_id == order_id, PaymentRecord.deleted_at.is_(None)).order_by(PaymentRecord.created_at.asc())
        ).all()

    def list_ledger_entries(self, order_id: str) -> list[InternalLedgerEntry]:
        return self.session.scalars(
            select(InternalLedgerEntry).where(InternalLedgerEntry.order_id == order_id).order_by(InternalLedgerEntry.created_at.asc())
        ).all()

    def _create_ledger_entry(
        self,
        *,
        order: OrderRecord,
        payment: PaymentRecord | None,
        entry_kind: str,
        direction: str,
        entry_state: str,
        amount: float | None,
        currency_code: str,
        reason_code: str,
        note: str | None,
        auth: AuthContext | None,
    ) -> InternalLedgerEntry:
        item = InternalLedgerEntry(
            code=reserve_code(self.session, "internal_ledger_entries", "LED"),
            order_id=order.id,
            payment_record_id=payment.id if payment else None,
            entry_kind=entry_kind,
            direction=direction,
            entry_state=entry_state,
            amount=amount,
            currency_code=currency_code,
            reason_code=reason_code,
            note=_clean_text(note),
            created_by_user_id=auth.user_id if auth else None,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def _recompute_order_shape(self, order: OrderRecord, lines: list[OrderLine]) -> None:
        ready_count = sum(1 for line in lines if line.readiness_state == "ready")
        delivered_count = sum(1 for line in lines if line.delivery_state == "delivered")
        refunded_count = sum(1 for line in lines if line.refund_state == "refunded")
        partial_refund_count = sum(1 for line in lines if line.refund_state == "partial_refund")
        disputed_count = sum(1 for line in lines if line.dispute_state == "open")
        total = len(lines)

        if total == 0:
            order.readiness_state = "not_ready"
            order.logistics_state = "planning"
            order.refund_state = "none"
            order.dispute_state = "clear"
            return

        if ready_count == 0:
            order.readiness_state = "not_ready"
        elif ready_count == total:
            order.readiness_state = "ready"
        else:
            order.readiness_state = "partial_ready"

        if delivered_count == 0:
            if order.readiness_state == "ready":
                order.logistics_state = "ready"
            elif order.readiness_state == "partial_ready":
                order.logistics_state = "ready_partial"
            elif order.logistics_state not in {"cancelled", "disputed"}:
                order.logistics_state = "planning"
        elif delivered_count == total:
            order.logistics_state = "delivered"
        else:
            order.logistics_state = "partial_delivery"

        if refunded_count == total and total > 0:
            order.refund_state = "refunded"
        elif refunded_count > 0 or partial_refund_count > 0:
            order.refund_state = "partial_refund"
        else:
            order.refund_state = "none"

        order.dispute_state = "open" if disputed_count else "clear"

    def _resolve_target_lines(self, order: OrderRecord, line_codes: list[str] | None) -> tuple[list[OrderLine], list[OrderLine]]:
        all_lines = self.list_order_lines(order.id)
        if not line_codes:
            return all_lines, all_lines
        target = [line for line in all_lines if line.code in set(line_codes)]
        if not target:
            raise HTTPException(status_code=404, detail="order_lines_not_found")
        return target, all_lines

    def _ensure_payment_record(
        self,
        *,
        order: OrderRecord,
        amount: float | None,
        currency_code: str,
        reason_code: str,
        note: str | None,
        auth: AuthContext | None,
    ) -> PaymentRecord:
        payment = PaymentRecord(
            code=reserve_code(self.session, "payment_records", "PAY"),
            order_id=order.id,
            payment_state="created",
            amount=amount,
            currency_code=currency_code,
            note=_clean_text(note),
            created_by_user_id=auth.user_id if auth else None,
            last_transition_reason_code=reason_code,
        )
        self.session.add(payment)
        self.session.flush()
        self._create_ledger_entry(
            order=order,
            payment=payment,
            entry_kind="payment_expected",
            direction="debit",
            entry_state="open",
            amount=amount,
            currency_code=currency_code,
            reason_code=reason_code,
            note=note or "Order created with internal payment expectation.",
            auth=auth,
        )
        return payment

    def create_order_from_offer(
        self,
        *,
        offer: OfferRecord,
        version: OfferVersion,
        request: RequestRecord,
        auth: AuthContext | None,
        reason_code: str,
        note: str | None = None,
    ) -> OrderBundle:
        existing = self.session.scalar(
            select(OrderRecord).where(OrderRecord.offer_id == offer.id, OrderRecord.offer_version_id == version.id, OrderRecord.deleted_at.is_(None))
        )
        self.workflow_support.evaluate_offer_to_order(
            offer=offer,
            version=version,
            request=request,
            existing_order=existing is not None,
        ).raise_if_blocked()
        order = OrderRecord(
            code=reserve_code(self.session, "orders", "ORD"),
            offer_id=offer.id,
            offer_version_id=version.id,
            request_id=request.id,
            customer_refs_json={
                "customer_ref": request.customer_ref,
                "customer_email": request.customer_email,
                "customer_name": request.customer_name,
                "customer_phone": request.customer_phone,
                "guest_company_name": request.guest_company_name,
            },
            supplier_refs_json=[value for value in [version.supplier_ref] if value],
            internal_owner_user_id=request.owner_user_id or request.assignee_user_id or (auth.user_id if auth else None),
            order_status="created",
            payment_state="created",
            logistics_state="planning",
            readiness_state="not_ready",
            refund_state="none",
            dispute_state="clear",
            public_status="accepted",
            acceptance_reason=note or reason_code,
            last_transition_reason_code=reason_code,
            last_transition_note=_clean_text(note),
        )
        self.session.add(order)
        self.session.flush()
        line = OrderLine(
            code=reserve_code(self.session, "order_lines", "ORL"),
            order_id=order.id,
            catalog_item_id=request.catalog_item_id,
            line_type="catalog_service" if request.catalog_item_id else "service_context",
            title=request.title or request.item_service_context or offer.public_summary or offer.code,
            quantity=1,
            unit_label="lot",
            line_amount=version.amount,
            currency_code=version.currency_code,
            line_status="created",
            planned_supplier_ref=version.supplier_ref,
            planned_stage_refs_json=["commercial_confirmed", "production_pending"],
            readiness_state="not_ready",
            delivery_state="pending",
            refund_state="none",
            dispute_state="clear",
            last_transition_reason_code=reason_code,
            last_transition_note=_clean_text(note),
        )
        self.session.add(line)
        self.session.flush()
        payment = self._ensure_payment_record(
            order=order,
            amount=float(version.amount) if version.amount is not None else None,
            currency_code=version.currency_code,
            reason_code=reason_code,
            note=note,
            auth=auth,
        )
        self.request_service.transition_request(
            request,
            target_status="converted_to_order",
            reason_code=reason_code,
            reason_note=note or "Confirmed offer version converted into order.",
            auth=auth,
        )
        record_audit_event(
            self.session,
            module_name="orders",
            action="order_created",
            entity_type="order",
            entity_id=order.id,
            entity_code=order.code,
            auth=auth,
            reason=reason_code,
            payload_json={"offer_code": offer.code, "offer_version_code": version.code, "payment_code": payment.code},
        )
        return OrderBundle(order=order, lines=[line], payments=[payment], ledger=self.list_ledger_entries(order.id))

    def apply_order_action(
        self,
        *,
        order: OrderRecord,
        action: str,
        auth: AuthContext | None,
        reason_code: str,
        note: str | None = None,
        supplier_ref: str | None = None,
        line_codes: list[str] | None = None,
    ) -> OrderBundle:
        if action not in ORDER_ACTIONS:
            raise HTTPException(status_code=422, detail="order_action_invalid")
        if order.order_status in {"cancelled", "completed"} and action not in {"dispute"}:
            raise HTTPException(status_code=409, detail="order_not_mutable")
        target_lines, all_lines = self._resolve_target_lines(order, line_codes)
        supplier_value = _clean_text(supplier_ref)
        supplier_assigned = any(line.planned_supplier_ref for line in all_lines) or bool(order.supplier_refs_json) or bool(supplier_value)
        self.workflow_support.evaluate_order_action(
            order=order,
            action=action,
            supplier_assigned=supplier_assigned,
            readiness_state=order.readiness_state,
            logistics_state=order.logistics_state,
        ).raise_if_blocked()

        # RU: Order-экшен работает как тонкий orchestration-слой и обновляет общий order shape без попытки строить MES-планировщик.
        if action == "assign_supplier":
            if not supplier_value:
                raise HTTPException(status_code=422, detail="supplier_ref_required")
            supplier_refs = list(order.supplier_refs_json or [])
            if supplier_value not in supplier_refs:
                supplier_refs.append(supplier_value)
            order.supplier_refs_json = supplier_refs
            order.order_status = "supplier_assigned"
            for line in target_lines:
                line.planned_supplier_ref = supplier_value
                line.line_status = "supplier_assigned"
                line.last_transition_reason_code = reason_code
                line.last_transition_note = _clean_text(note)
        elif action == "confirm_start":
            if not any(line.planned_supplier_ref for line in all_lines):
                raise HTTPException(status_code=409, detail="supplier_assignment_required")
            order.order_status = "confirmed_start"
            for line in target_lines:
                line.line_status = "started"
                line.last_transition_reason_code = reason_code
                line.last_transition_note = _clean_text(note)
        elif action == "mark_production":
            if order.order_status not in {"confirmed_start", "supplier_assigned", "in_production", "partially_ready"}:
                raise HTTPException(status_code=409, detail="order_not_ready_for_production")
            order.order_status = "in_production"
            for line in target_lines:
                line.line_status = "in_production"
                line.last_transition_reason_code = reason_code
                line.last_transition_note = _clean_text(note)
        elif action == "ready":
            if order.order_status not in {"confirmed_start", "in_production", "supplier_assigned", "partially_ready"}:
                raise HTTPException(status_code=409, detail="order_not_ready_for_readiness_update")
            full_ready = len(target_lines) == len(all_lines)
            order.order_status = "ready" if full_ready else "partially_ready"
            order.logistics_state = "ready" if full_ready else "ready_partial"
            for line in target_lines:
                line.line_status = "ready"
                line.readiness_state = "ready"
                line.last_transition_reason_code = reason_code
                line.last_transition_note = _clean_text(note)
        elif action == "delivery":
            if order.readiness_state not in {"ready", "partial_ready"}:
                raise HTTPException(status_code=409, detail="order_not_ready_for_delivery")
            full_delivery = len(target_lines) == len(all_lines)
            order.order_status = "in_delivery" if full_delivery else "partially_delivered"
            order.logistics_state = "delivered" if full_delivery else "partial_delivery"
            for line in target_lines:
                line.line_status = "delivered"
                line.delivery_state = "delivered"
                line.readiness_state = "ready"
                line.last_transition_reason_code = reason_code
                line.last_transition_note = _clean_text(note)
        elif action == "complete":
            if order.logistics_state not in {"delivered", "partial_delivery"}:
                raise HTTPException(status_code=409, detail="order_not_ready_for_completion")
            order.order_status = "completed"
            order.logistics_state = "delivered"
            for line in all_lines:
                line.line_status = "completed"
                line.delivery_state = "delivered"
                line.readiness_state = "ready"
                line.last_transition_reason_code = reason_code
                line.last_transition_note = _clean_text(note)
        elif action == "cancel":
            order.order_status = "cancelled"
            order.logistics_state = "cancelled"
            for line in all_lines:
                line.line_status = "cancelled"
                line.last_transition_reason_code = reason_code
                line.last_transition_note = _clean_text(note)
        elif action == "dispute":
            if order.order_status == "cancelled":
                raise HTTPException(status_code=409, detail="cancelled_order_cannot_open_dispute")
            order.order_status = "disputed"
            order.dispute_state = "open"
            for line in target_lines:
                line.line_status = "disputed"
                line.dispute_state = "open"
                line.last_transition_reason_code = reason_code
                line.last_transition_note = _clean_text(note)

        order.last_transition_reason_code = reason_code
        order.last_transition_note = _clean_text(note)
        self._recompute_order_shape(order, all_lines)
        record_audit_event(
            self.session,
            module_name="orders",
            action=f"order_{action}",
            entity_type="order",
            entity_id=order.id,
            entity_code=order.code,
            auth=auth,
            reason=reason_code,
            payload_json={
                "line_codes": [line.code for line in target_lines],
                "supplier_ref": supplier_value,
                "order_status": order.order_status,
                "payment_state": order.payment_state,
                "logistics_state": order.logistics_state,
            },
        )
        return OrderBundle(order=order, lines=all_lines, payments=self.list_payment_records(order.id), ledger=self.list_ledger_entries(order.id))

    def create_payment_record(
        self,
        *,
        order: OrderRecord,
        amount: float | None,
        currency_code: str,
        payment_ref: str | None,
        provider_ref: str | None,
        reason_code: str,
        note: str | None,
        auth: AuthContext | None,
    ) -> PaymentRecord:
        item = PaymentRecord(
            code=reserve_code(self.session, "payment_records", "PAY"),
            order_id=order.id,
            payment_state="created",
            amount=amount,
            currency_code=currency_code,
            payment_ref=_clean_text(payment_ref),
            provider_ref=_clean_text(provider_ref),
            note=_clean_text(note),
            created_by_user_id=auth.user_id if auth else None,
            last_transition_reason_code=reason_code,
        )
        self.session.add(item)
        self.session.flush()
        self._create_ledger_entry(
            order=order,
            payment=item,
            entry_kind="payment_expected",
            direction="debit",
            entry_state="open",
            amount=amount,
            currency_code=currency_code,
            reason_code=reason_code,
            note=note or "Additional internal payment expectation added.",
            auth=auth,
        )
        record_audit_event(
            self.session,
            module_name="orders",
            action="payment_record_created",
            entity_type="payment_record",
            entity_id=item.id,
            entity_code=item.code,
            auth=auth,
            reason=reason_code,
            payload_json={"order_code": order.code, "payment_state": item.payment_state},
        )
        return item

    def transition_payment_record(
        self,
        *,
        payment: PaymentRecord,
        target_state: str,
        reason_code: str,
        note: str | None,
        auth: AuthContext | None,
    ) -> OrderBundle:
        if target_state not in PAYMENT_STATES:
            raise HTTPException(status_code=422, detail="payment_state_invalid")
        if target_state not in ORDER_PAYMENT_TRANSITIONS[payment.payment_state]:
            raise HTTPException(status_code=409, detail="payment_transition_not_allowed")
        order = self.session.scalar(select(OrderRecord).where(OrderRecord.id == payment.order_id))
        if order is None:
            raise HTTPException(status_code=404, detail="order_not_found")
        payment.payment_state = target_state
        payment.note = _clean_text(note) or payment.note
        payment.last_transition_reason_code = reason_code
        if target_state == "confirmed":
            payment.confirmed_at = utc_now()
            order.payment_state = "confirmed"
        elif target_state == "pending":
            order.payment_state = "pending"
        elif target_state == "failed":
            payment.failed_at = utc_now()
            order.payment_state = "failed"
        elif target_state == "partially_refunded":
            payment.refunded_at = utc_now()
            order.payment_state = "partially_refunded"
            order.refund_state = "partial_refund"
            for line in self.list_order_lines(order.id):
                if line.refund_state == "none":
                    line.refund_state = "partial_refund"
                    break
        elif target_state == "refunded":
            payment.refunded_at = utc_now()
            order.payment_state = "refunded"
            order.refund_state = "refunded"
            for line in self.list_order_lines(order.id):
                line.refund_state = "refunded"
        ledger_kind = {
            "pending": "payment_pending",
            "confirmed": "payment_confirmed",
            "failed": "payment_failed",
            "partially_refunded": "refund_partial",
            "refunded": "refund_full",
        }[target_state]
        direction = "credit" if target_state == "confirmed" else "debit"
        self._create_ledger_entry(
            order=order,
            payment=payment,
            entry_kind=ledger_kind,
            direction=direction,
            entry_state=target_state,
            amount=float(payment.amount) if payment.amount is not None else None,
            currency_code=payment.currency_code,
            reason_code=reason_code,
            note=note,
            auth=auth,
        )
        record_audit_event(
            self.session,
            module_name="orders",
            action="payment_record_updated",
            entity_type="payment_record",
            entity_id=payment.id,
            entity_code=payment.code,
            auth=auth,
            reason=reason_code,
            payload_json={"order_code": order.code, "payment_state": target_state},
        )
        return OrderBundle(order=order, lines=self.list_order_lines(order.id), payments=self.list_payment_records(order.id), ledger=self.list_ledger_entries(order.id))
