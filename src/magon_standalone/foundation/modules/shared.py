# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from datetime import datetime


def iso_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def company_public_view(company) -> dict[str, object]:
    return {
        "id": company.id,
        "code": company.code,
        "name": company.public_name,
        "country_code": company.country_code,
        "status": company.public_status,
        "note": company.public_note,
    }


def company_operator_view(company) -> dict[str, object]:
    return {
        **company_public_view(company),
        "legal_name": company.legal_name,
        "internal_status": company.internal_status,
        "internal_note": company.internal_note,
        "owner_user_id": company.owner_user_id,
        "archived_at": iso_or_none(company.archived_at),
        "deleted_at": iso_or_none(company.deleted_at),
        "created_at": iso_or_none(company.created_at),
        "updated_at": iso_or_none(company.updated_at),
    }


def company_contact_view(contact) -> dict[str, object]:
    return {
        "id": contact.id,
        "code": contact.code,
        "contact_name": contact.contact_name,
        "role_label": contact.role_label,
        "email": contact.email,
        "phone": contact.phone,
        "is_primary": contact.is_primary,
        "verification_status": contact.verification_status,
        "source_note": contact.source_note,
    }


def company_address_view(address) -> dict[str, object]:
    return {
        "id": address.id,
        "code": address.code,
        "label": address.label,
        "raw_address": address.raw_address,
        "normalized_address": address.normalized_address,
        "city": address.city,
        "district": address.district,
        "region": address.region,
        "postal_code": address.postal_code,
        "country_code": address.country_code,
        "is_primary": address.is_primary,
    }


def supplier_public_view(supplier) -> dict[str, object]:
    return {
        "id": supplier.id,
        "code": supplier.code,
        "display_name": supplier.display_name,
        "canonical_name": supplier.canonical_name,
        "trust_level": supplier.trust_level,
        "capability_summary": supplier.capability_summary,
        "website": supplier.website,
    }


def supplier_operator_view(supplier) -> dict[str, object]:
    return {
        **supplier_public_view(supplier),
        "company_id": supplier.company_id,
        "source_registry_id": supplier.source_registry_id,
        "supplier_status": supplier.supplier_status,
        "dedup_status": supplier.dedup_status,
        "canonical_email": supplier.canonical_email,
        "canonical_phone": supplier.canonical_phone,
        "capabilities_json": list(supplier.capabilities_json or []),
        "confidence_score": float(supplier.confidence_score) if supplier.confidence_score is not None else None,
        "contact_confirmed_at": iso_or_none(supplier.contact_confirmed_at),
        "capability_confirmed_at": iso_or_none(supplier.capability_confirmed_at),
        "trusted_at": iso_or_none(supplier.trusted_at),
        "blocked_at": iso_or_none(supplier.blocked_at),
        "blocked_reason": supplier.blocked_reason,
        "archived_at": iso_or_none(supplier.archived_at),
        "deleted_at": iso_or_none(supplier.deleted_at),
        "created_at": iso_or_none(supplier.created_at),
        "updated_at": iso_or_none(supplier.updated_at),
    }


def supplier_site_view(site) -> dict[str, object]:
    return {
        "id": site.id,
        "code": site.code,
        "supplier_company_id": site.supplier_company_id,
        "address_id": site.address_id,
        "site_name": site.site_name,
        "site_status": site.site_status,
        "trust_level": site.trust_level,
        "capability_summary": site.capability_summary,
        "current_load_percent": site.current_load_percent,
        "lead_time_days": site.lead_time_days,
        "is_primary": site.is_primary,
        "created_at": iso_or_none(site.created_at),
        "updated_at": iso_or_none(site.updated_at),
    }


def catalog_public_view(item) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "title": item.public_title,
        "description": item.public_description,
        "category_code": item.category_code,
        "category_label": item.category_label,
        "tags": list(item.tags_json or []),
        "option_summaries": list(item.option_summaries_json or []),
        "currency_code": item.currency_code,
        "list_price": float(item.list_price) if item.list_price is not None else None,
        "pricing_mode": item.pricing_mode,
        "pricing_summary": item.pricing_summary,
        "pricing_note": item.pricing_note,
        "mode": item.catalog_mode,
        "visibility": item.visibility,
        "translations": dict(item.translations_json or {}),
        "is_featured": item.is_featured,
    }


def catalog_operator_view(item) -> dict[str, object]:
    return {
        **catalog_public_view(item),
        "internal_title": item.internal_title,
        "internal_description": item.internal_description,
        "supplier_id": item.supplier_id,
        "supplier_company_id": item.supplier_company_id,
        "sort_order": item.sort_order,
        "archived_at": iso_or_none(item.archived_at),
        "deleted_at": iso_or_none(item.deleted_at),
        "created_at": iso_or_none(item.created_at),
        "updated_at": iso_or_none(item.updated_at),
    }


def draft_public_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "catalog_item_id": record.catalog_item_id,
        "submitted_request_id": record.submitted_request_id,
        "title": record.title,
        "summary": record.summary,
        "item_service_context": record.item_service_context,
        "customer_name": record.customer_name,
        "customer_email": record.customer_email,
        "customer_phone": record.customer_phone,
        "guest_company_name": record.guest_company_name,
        "city": record.city,
        "geo": dict(record.geo_json or {}),
        "source_channel": record.source_channel,
        "draft_status": record.draft_status,
        "public_status": record.public_status,
        "internal_status": record.internal_status,
        "intake_channel": record.intake_channel,
        "locale_code": record.locale_code,
        "requested_deadline_at": iso_or_none(record.requested_deadline_at),
        "requested_due_at": iso_or_none(record.requested_due_at),
        "owner_user_id": record.owner_user_id,
        "assignee_user_id": record.assignee_user_id,
        "last_autosaved_at": iso_or_none(record.last_autosaved_at),
        "last_customer_activity_at": iso_or_none(record.last_customer_activity_at),
        "abandoned_at": iso_or_none(record.abandoned_at),
        "last_transition_reason_code": record.last_transition_reason_code,
        "last_transition_note": record.last_transition_note,
        "submitted_at": iso_or_none(record.submitted_at),
        "created_at": iso_or_none(record.created_at),
        "updated_at": iso_or_none(record.updated_at),
    }


def request_operator_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "customer_ref": record.customer_ref,
        "draft_request_id": record.draft_request_id,
        "company_id": record.company_id,
        "catalog_item_id": record.catalog_item_id,
        "customer_email": record.customer_email,
        "customer_name": record.customer_name,
        "customer_phone": record.customer_phone,
        "guest_company_name": record.guest_company_name,
        "title": record.title,
        "summary": record.summary,
        "item_service_context": record.item_service_context,
        "source_channel": record.source_channel,
        "city": record.city,
        "geo": dict(record.geo_json or {}),
        "request_status": record.request_status,
        "locale_code": record.locale_code,
        "requested_deadline_at": iso_or_none(record.requested_deadline_at),
        "requested_due_at": iso_or_none(record.requested_due_at),
        "owner_user_id": record.owner_user_id,
        "assignee_user_id": record.assignee_user_id,
        "intake_reason": record.intake_reason,
        "last_transition_reason_code": record.last_transition_reason_code,
        "last_transition_note": record.last_transition_note,
        "created_at": iso_or_none(record.created_at),
        "updated_at": iso_or_none(record.updated_at),
    }


def required_field_state_view(item) -> dict[str, object]:
    return {
        "code": item.code,
        "owner_type": item.owner_type,
        "owner_id": item.owner_id,
        "field_name": item.field_name,
        "is_required": item.is_required,
        "field_status": item.field_status,
        "message": item.message,
        "current_value": item.current_value,
        "last_checked_at": iso_or_none(item.last_checked_at),
    }


def intake_file_link_view(item) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "owner_type": item.owner_type,
        "owner_id": item.owner_id,
        "label": item.label,
        "file_url": item.file_url,
        "file_kind": item.file_kind,
        "visibility": item.visibility,
        "created_by_user_id": item.created_by_user_id,
        "created_at": iso_or_none(item.created_at),
    }


def request_reason_view(item) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "reason_kind": item.reason_kind,
        "reason_code": item.reason_code,
        "note": item.note,
        "is_active": item.is_active,
        "created_by_user_id": item.created_by_user_id,
        "resolved_by_user_id": item.resolved_by_user_id,
        "resolved_at": iso_or_none(item.resolved_at),
        "created_at": iso_or_none(item.created_at),
    }


def clarification_cycle_view(item) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "request_id": item.request_id,
        "cycle_index": item.cycle_index,
        "cycle_status": item.cycle_status,
        "opened_reason_code": item.opened_reason_code,
        "opened_note": item.opened_note,
        "opened_by_user_id": item.opened_by_user_id,
        "closed_by_user_id": item.closed_by_user_id,
        "closed_at": iso_or_none(item.closed_at),
        "created_at": iso_or_none(item.created_at),
    }


def follow_up_item_view(item) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "request_id": item.request_id,
        "clarification_cycle_id": item.clarification_cycle_id,
        "title": item.title,
        "detail": item.detail,
        "follow_up_status": item.follow_up_status,
        "owner_user_id": item.owner_user_id,
        "due_at": iso_or_none(item.due_at),
        "customer_visible": item.customer_visible,
        "closed_reason_code": item.closed_reason_code,
        "closed_at": iso_or_none(item.closed_at),
        "created_at": iso_or_none(item.created_at),
    }


def timeline_event_view(item) -> dict[str, object]:
    reason_code = getattr(item, "reason_code", None) or getattr(item, "reason", None)
    occurred_at = getattr(item, "occurred_at", None) or getattr(item, "created_at", None)
    return {
        "code": item.code,
        "entry_kind": getattr(item, "entry_kind", "event"),
        "module_name": getattr(item, "module_name", None),
        "action": getattr(item, "action", None) or getattr(item, "event_type", None),
        "event_type": getattr(item, "event_type", None) or getattr(item, "action", None),
        "message_type": getattr(item, "message_type", None),
        "entity_type": getattr(item, "entity_type", None) or getattr(item, "owner_type", None),
        "entity_code": getattr(item, "entity_code", None),
        "actor_role": getattr(item, "actor_role", None),
        "reason": getattr(item, "reason", None),
        "reason_code": reason_code,
        "title": getattr(item, "title", None),
        "body": getattr(item, "body", None),
        "visibility_scope": getattr(item, "visibility_scope", None) or getattr(item, "visibility", None),
        "payload": dict(item.payload_json or {}),
        "created_at": iso_or_none(occurred_at),
    }


def file_check_view(item) -> dict[str, object]:
    return {
        "code": item.code,
        "check_kind": item.check_kind,
        "check_state": item.check_state,
        "reason_code": item.reason_code,
        "message": item.message,
        "created_at": iso_or_none(item.created_at),
    }


def file_version_view(item) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "version_no": item.version_no,
        "version_status": item.version_status,
        "original_name": item.original_name,
        "storage_backend": item.storage_backend,
        "mime_type": item.mime_type,
        "file_extension": item.file_extension,
        "byte_size": item.byte_size,
        "file_type": item.file_type,
        "check_state": item.check_state,
        "visibility_scope": item.visibility_scope,
        "final_flag": item.final_flag,
        "created_by_user_id": item.created_by_user_id,
        "created_at": iso_or_none(item.created_at),
    }


def file_asset_view(item, *, latest_version=None, checks: list | None = None, download_url: str | None = None) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "owner_type": item.owner_type,
        "owner_id": item.owner_id,
        "file_type": item.file_type,
        "title": item.title,
        "original_name": item.original_name,
        "mime_type": item.mime_type,
        "file_extension": item.file_extension,
        "byte_size": item.byte_size,
        "current_version_no": item.current_version_no,
        "check_state": item.check_state,
        "visibility_scope": item.visibility_scope,
        "final_flag": item.final_flag,
        "uploaded_by_user_id": item.uploaded_by_user_id,
        "latest_version": file_version_view(latest_version) if latest_version else None,
        "checks": [file_check_view(check) for check in (checks or [])],
        "download_url": download_url,
        "created_at": iso_or_none(item.created_at),
        "updated_at": iso_or_none(item.updated_at),
    }


def document_version_view(item, *, download_url: str | None = None) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "version_no": item.version_no,
        "version_status": item.version_status,
        "file_asset_id": item.file_asset_id,
        "file_version_id": item.file_version_id,
        "sent_state": item.sent_state,
        "confirmation_state": item.confirmation_state,
        "reason_code": item.reason_code,
        "note": item.note,
        "visibility_scope": item.visibility_scope,
        "payload": dict(item.payload_json or {}),
        "download_url": download_url,
        "published_at": iso_or_none(item.published_at),
        "sent_at": iso_or_none(item.sent_at),
        "confirmed_at": iso_or_none(item.confirmed_at),
        "replaced_at": iso_or_none(item.replaced_at),
        "created_at": iso_or_none(item.created_at),
    }


def document_view(item, *, current_version=None, download_url: str | None = None) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "owner_type": item.owner_type,
        "owner_id": item.owner_id,
        "document_type": item.document_type,
        "template_key": item.template_key,
        "title": item.title,
        "visibility_scope": item.visibility_scope,
        "current_version_no": item.current_version_no,
        "published_version_no": item.published_version_no,
        "sent_state": item.sent_state,
        "confirmation_state": item.confirmation_state,
        "file_id": item.file_id,
        "created_by_user_id": item.created_by_user_id,
        "current_version": document_version_view(current_version, download_url=download_url) if current_version else None,
        "download_url": download_url,
        "created_at": iso_or_none(item.created_at),
        "updated_at": iso_or_none(item.updated_at),
    }


def offer_operator_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "request_id": record.request_id,
        "request_ref": record.request_ref,
        "current_version_no": record.current_version_no,
        "offer_status": record.offer_status,
        "confirmation_state": record.confirmation_state,
        "amount": float(record.amount) if record.amount is not None else None,
        "currency_code": record.currency_code,
        "lead_time_days": record.lead_time_days,
        "terms_text": record.terms_text,
        "scenario_type": record.scenario_type,
        "supplier_ref": record.supplier_ref,
        "public_summary": record.public_summary,
        "transition_reason": record.transition_reason,
        "created_at": iso_or_none(record.created_at),
        "updated_at": iso_or_none(record.updated_at),
    }


def offer_version_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "offer_id": record.offer_id,
        "version_no": record.version_no,
        "version_status": record.version_status,
        "confirmation_state": record.confirmation_state,
        "amount": float(record.amount) if record.amount is not None else None,
        "currency_code": record.currency_code,
        "lead_time_days": record.lead_time_days,
        "terms_text": record.terms_text,
        "scenario_type": record.scenario_type,
        "supplier_ref": record.supplier_ref,
        "public_summary": record.public_summary,
        "change_reason_code": record.change_reason_code,
        "change_note": record.change_note,
        "is_current": record.is_current,
        "created_at": iso_or_none(record.created_at),
        "updated_at": iso_or_none(record.updated_at),
    }


def offer_confirmation_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "offer_id": record.offer_id,
        "offer_version_id": record.offer_version_id,
        "confirmation_action": record.confirmation_action,
        "confirmation_state": record.confirmation_state,
        "reason_code": record.reason_code,
        "note": record.note,
        "actor_user_id": record.actor_user_id,
        "actor_role": record.actor_role,
        "occurred_at": iso_or_none(record.occurred_at),
        "created_at": iso_or_none(record.created_at),
    }


def offer_comparison_metadata_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "offer_id": record.offer_id,
        "offer_version_id": record.offer_version_id,
        "comparison_title": record.comparison_title,
        "comparison_rank": record.comparison_rank,
        "recommended": record.recommended,
        "highlights": list(record.highlights_json or []),
        "metadata": dict(record.metadata_json or {}),
        "created_at": iso_or_none(record.created_at),
    }


def offer_reset_reason_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "offer_id": record.offer_id,
        "previous_offer_version_id": record.previous_offer_version_id,
        "new_offer_version_id": record.new_offer_version_id,
        "previous_confirmation_state": record.previous_confirmation_state,
        "reason_code": record.reason_code,
        "note": record.note,
        "created_by_user_id": record.created_by_user_id,
        "created_at": iso_or_none(record.created_at),
    }


def order_operator_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "offer_id": record.offer_id,
        "offer_version_id": record.offer_version_id,
        "request_id": record.request_id,
        "customer_refs": dict(record.customer_refs_json or {}),
        "supplier_refs": list(record.supplier_refs_json or []),
        "internal_owner_user_id": record.internal_owner_user_id,
        "order_status": record.order_status,
        "payment_state": record.payment_state,
        "logistics_state": record.logistics_state,
        "readiness_state": record.readiness_state,
        "refund_state": record.refund_state,
        "dispute_state": record.dispute_state,
        "public_status": record.public_status,
        "acceptance_reason": record.acceptance_reason,
        "last_transition_reason_code": record.last_transition_reason_code,
        "last_transition_note": record.last_transition_note,
        "created_at": iso_or_none(record.created_at),
        "updated_at": iso_or_none(record.updated_at),
    }


def order_public_view(record) -> dict[str, object]:
    return {
        "code": record.code,
        "order_status": record.order_status,
        "payment_state": record.payment_state,
        "logistics_state": record.logistics_state,
        "readiness_state": record.readiness_state,
        "refund_state": record.refund_state,
        "dispute_state": record.dispute_state,
        "public_status": record.public_status,
        "created_at": iso_or_none(record.created_at),
        "updated_at": iso_or_none(record.updated_at),
    }


def order_line_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "order_id": record.order_id,
        "catalog_item_id": record.catalog_item_id,
        "line_type": record.line_type,
        "title": record.title,
        "quantity": float(record.quantity) if record.quantity is not None else None,
        "unit_label": record.unit_label,
        "line_amount": float(record.line_amount) if record.line_amount is not None else None,
        "currency_code": record.currency_code,
        "line_status": record.line_status,
        "planned_supplier_ref": record.planned_supplier_ref,
        "planned_stage_refs": list(record.planned_stage_refs_json or []),
        "readiness_state": record.readiness_state,
        "delivery_state": record.delivery_state,
        "refund_state": record.refund_state,
        "dispute_state": record.dispute_state,
        "last_transition_reason_code": record.last_transition_reason_code,
        "last_transition_note": record.last_transition_note,
        "created_at": iso_or_none(record.created_at),
        "updated_at": iso_or_none(record.updated_at),
    }


def payment_record_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "order_id": record.order_id,
        "payment_state": record.payment_state,
        "amount": float(record.amount) if record.amount is not None else None,
        "currency_code": record.currency_code,
        "payment_ref": record.payment_ref,
        "provider_ref": record.provider_ref,
        "note": record.note,
        "created_by_user_id": record.created_by_user_id,
        "confirmed_at": iso_or_none(record.confirmed_at),
        "failed_at": iso_or_none(record.failed_at),
        "refunded_at": iso_or_none(record.refunded_at),
        "last_transition_reason_code": record.last_transition_reason_code,
        "created_at": iso_or_none(record.created_at),
        "updated_at": iso_or_none(record.updated_at),
    }


def ledger_entry_view(record) -> dict[str, object]:
    return {
        "id": record.id,
        "code": record.code,
        "order_id": record.order_id,
        "payment_record_id": record.payment_record_id,
        "entry_kind": record.entry_kind,
        "direction": record.direction,
        "entry_state": record.entry_state,
        "amount": float(record.amount) if record.amount is not None else None,
        "currency_code": record.currency_code,
        "reason_code": record.reason_code,
        "note": record.note,
        "created_by_user_id": record.created_by_user_id,
        "created_at": iso_or_none(record.created_at),
    }
