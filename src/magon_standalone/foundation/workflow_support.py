from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import Select, desc, or_, select
from sqlalchemy.orm import Session

from .codes import reserve_code
from .db import utc_now
from .models import (
    AuditEvent,
    Document,
    EscalationHint,
    FileAsset,
    MessageEvent,
    NotificationRule,
    OfferRecord,
    OrderRecord,
    ReasonCodeCatalog,
    RequestRecord,
    RuleDefinition,
    RuleVersion,
    SupplierCompany,
)
from .security import ROLE_ADMIN, ROLE_CUSTOMER, ROLE_GUEST, ROLE_OPERATOR

VISIBILITY_PUBLIC = "public"
VISIBILITY_INTERNAL = "internal"
VISIBILITY_CUSTOMER = "customer"
VISIBILITY_SUPPLIER = "supplier"

KEY_OBJECT_MODELS = {
    "request": RequestRecord,
    "offer": OfferRecord,
    "order": OrderRecord,
    "supplier": SupplierCompany,
    "supplier_company": SupplierCompany,
    "file": FileAsset,
    "file_asset": FileAsset,
    "document": Document,
}

BASELINE_REASON_CODES: list[dict[str, Any]] = [
    {
        "code": "draft_required_fields_missing",
        "title": "Не заполнены обязательные поля черновика",
        "category": "draft",
        "severity": "warning",
        "default_visibility_scope": VISIBILITY_CUSTOMER,
        "description": "Черновик нельзя перевести в заявку, пока не заполнены обязательные поля первой волны.",
    },
    {
        "code": "request_transition_not_allowed",
        "title": "Переход заявки запрещён",
        "category": "request",
        "severity": "warning",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Текущий статус заявки не допускает запрошенный переход.",
    },
    {
        "code": "request_has_active_blockers",
        "title": "У заявки есть активные блокеры",
        "category": "request",
        "severity": "critical",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "До устранения блокеров нельзя двигать заявку в следующий рабочий статус.",
    },
    {
        "code": "missing_artwork",
        "title": "Отсутствует artwork",
        "category": "request",
        "severity": "critical",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Клиент ещё не предоставил обязательные макеты или artwork.",
    },
    {
        "code": "customer_clarification_needed",
        "title": "Нужно уточнение от клиента",
        "category": "request",
        "severity": "warning",
        "default_visibility_scope": VISIBILITY_CUSTOMER,
        "description": "Заявка переведена в цикл уточнения и ждёт данных от клиента.",
    },
    {
        "code": "offer_version_not_confirmed",
        "title": "Версия предложения не подтверждена",
        "category": "offer",
        "severity": "critical",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Заказ можно создать только из подтверждённой версии предложения.",
    },
    {
        "code": "offer_sent_to_customer",
        "title": "Предложение отправлено клиенту",
        "category": "offer",
        "severity": "info",
        "default_visibility_scope": VISIBILITY_CUSTOMER,
        "description": "Клиенту отправлена конкретная версия предложения.",
    },
    {
        "code": "confirmed_offer_converted_to_order",
        "title": "Подтверждённое предложение переведено в заказ",
        "category": "order",
        "severity": "info",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Подтверждённая версия предложения стала основанием для нового заказа.",
    },
    {
        "code": "supplier_assignment_required",
        "title": "Нужно назначить поставщика",
        "category": "order",
        "severity": "critical",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Критичное действие по заказу невозможно без назначенного поставщика.",
    },
    {
        "code": "order_not_ready_for_production",
        "title": "Заказ нельзя запускать в производство",
        "category": "order",
        "severity": "critical",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Производственный старт требует корректного текущего состояния заказа.",
    },
    {
        "code": "order_not_ready_for_readiness_update",
        "title": "Заказ нельзя переводить в ready",
        "category": "order",
        "severity": "warning",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Статус готовности можно обновлять только после корректного производственного старта.",
    },
    {
        "code": "order_not_ready_for_delivery",
        "title": "Заказ нельзя переводить в доставку",
        "category": "order",
        "severity": "warning",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "В доставку попадает только заказ с подтверждённой готовностью.",
    },
    {
        "code": "order_not_ready_for_completion",
        "title": "Заказ нельзя завершить",
        "category": "order",
        "severity": "warning",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Финальное завершение допустимо только после доставки.",
    },
    {
        "code": "document_sent_to_customer",
        "title": "Документ отправлен клиенту",
        "category": "document",
        "severity": "info",
        "default_visibility_scope": VISIBILITY_CUSTOMER,
        "description": "Клиенту отправлена актуальная версия документа.",
    },
    {
        "code": "document_confirmation_recorded",
        "title": "Подтверждение документа зафиксировано",
        "category": "document",
        "severity": "info",
        "default_visibility_scope": VISIBILITY_CUSTOMER,
        "description": "Получено подтверждение по отправленной версии документа.",
    },
    {
        "code": "supplier_blocked_manual",
        "title": "Поставщик заблокирован вручную",
        "category": "supplier",
        "severity": "critical",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Поставщик или площадка заблокированы оператором/админом.",
    },
    {
        "code": "overdue_request_deadline",
        "title": "Просрочен дедлайн заявки",
        "category": "sla",
        "severity": "critical",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Текущий срок по заявке просрочен относительно запрошенного дедлайна.",
    },
    {
        "code": "overdue_offer_confirmation",
        "title": "Просрочено ожидание подтверждения предложения",
        "category": "sla",
        "severity": "warning",
        "default_visibility_scope": VISIBILITY_INTERNAL,
        "description": "Отправленное предложение слишком долго ожидает подтверждения клиента.",
    },
]

BASELINE_RULES: list[dict[str, Any]] = [
    {
        "code": "RULE-00001",
        "name": "draft-submit-required-fields",
        "scope": "drafts_requests.submit",
        "rule_kind": "transition_guard",
        "description": "Черновик нельзя переводить в Request без обязательных полей первой волны.",
        "config_json": {
            "required_fields": ["customer_email", "title", "summary", "item_service_context", "city", "requested_deadline_at"],
            "file_requirement": "optional",
        },
        "metadata_json": {"critical": True, "audience": "customer"},
        "version": {
            "version_no": 1,
            "version_status": "active",
            "metadata_json": {"source": "wave1_spec", "change_note": "Первая волна intake guards."},
            "explainability_json": {
                "summary": "Проверка обязательных полей draft перед submit.",
                "checks": ["required_fields", "file_requirement", "blockers"],
            },
        },
    },
    {
        "code": "RULE-00002",
        "name": "request-transition-blockers",
        "scope": "drafts_requests.transition",
        "rule_kind": "transition_guard",
        "description": "Нельзя двигать Request дальше при активных блокерах и невалидном статусном переходе.",
        "config_json": {"blocked_targets_except": ["needs_clarification", "cancelled"]},
        "metadata_json": {"critical": True, "audience": "operator"},
        "version": {
            "version_no": 1,
            "version_status": "active",
            "metadata_json": {"source": "wave1_spec", "change_note": "Первый request blocker guard."},
            "explainability_json": {
                "summary": "Переход заявки учитывает status graph и активные blockers.",
                "checks": ["transition_graph", "active_blockers"],
            },
        },
    },
    {
        "code": "RULE-00003",
        "name": "offer-convert-confirmed-version",
        "scope": "offers.convert_to_order",
        "rule_kind": "critical_action",
        "description": "Заказ создаётся только из подтверждённой версии предложения и допустимого статуса Request.",
        "config_json": {"request_status": "offer_sent", "confirmation_state": "accepted"},
        "metadata_json": {"critical": True, "audience": "operator"},
        "version": {
            "version_no": 1,
            "version_status": "active",
            "metadata_json": {"source": "wave1_spec", "change_note": "Order conversion guard."},
            "explainability_json": {
                "summary": "Проверка подтверждения конкретной версии offer перед order conversion.",
                "checks": ["confirmation_state", "request_status", "existing_order_guard"],
            },
        },
    },
    {
        "code": "RULE-00004",
        "name": "order-critical-actions",
        "scope": "orders.critical_action",
        "rule_kind": "critical_action",
        "description": "Критичные действия по заказу требуют валидного supplier/readiness/delivery состояния.",
        "config_json": {"actions": ["confirm_start", "mark_production", "ready", "delivery", "complete"]},
        "metadata_json": {"critical": True, "audience": "operator"},
        "version": {
            "version_no": 1,
            "version_status": "active",
            "metadata_json": {"source": "wave1_spec", "change_note": "Order critical action guards."},
            "explainability_json": {
                "summary": "Проверка supplier assignment, readiness и delivery перед критичными order actions.",
                "checks": ["supplier_assignment", "order_state", "line_state"],
            },
        },
    },
    {
        "code": "RULE-00005",
        "name": "baseline-notifications",
        "scope": "comms.notifications",
        "rule_kind": "notification",
        "description": "Базовые role-scoped уведомления первой волны с антиспам-защитой.",
        "config_json": {"transport": "inbox"},
        "metadata_json": {"critical": False, "audience": "all"},
        "version": {
            "version_no": 1,
            "version_status": "active",
            "metadata_json": {"source": "wave1_spec", "change_note": "Baseline notifications."},
            "explainability_json": {
                "summary": "Генерация уведомлений по событиям с suppression по dedupe window.",
                "checks": ["rule_match", "visibility_scope", "spam_guard"],
            },
        },
    },
]

BASELINE_NOTIFICATION_RULES: list[dict[str, Any]] = [
    {
        "code": "NTF-00001",
        "rule_code": "RULE-00005",
        "entity_type": "request",
        "event_type": "request_status_changed",
        "recipient_scope": VISIBILITY_CUSTOMER,
        "channel": "inbox",
        "template_key": "request_clarification_needed",
        "min_interval_seconds": 3600,
        "metadata_json": {"status_in": ["needs_clarification"]},
    },
    {
        "code": "NTF-00002",
        "rule_code": "RULE-00005",
        "entity_type": "offer",
        "event_type": "offer_sent",
        "recipient_scope": VISIBILITY_CUSTOMER,
        "channel": "inbox",
        "template_key": "offer_sent_customer",
        "min_interval_seconds": 3600,
    },
    {
        "code": "NTF-00003",
        "rule_code": "RULE-00005",
        "entity_type": "order",
        "event_type": "order_created",
        "recipient_scope": VISIBILITY_INTERNAL,
        "channel": "inbox",
        "template_key": "order_created_internal",
        "min_interval_seconds": 900,
    },
    {
        "code": "NTF-00004",
        "rule_code": "RULE-00005",
        "entity_type": "document",
        "event_type": "document_sent",
        "recipient_scope": VISIBILITY_CUSTOMER,
        "channel": "inbox",
        "template_key": "document_sent_customer",
        "min_interval_seconds": 3600,
    },
    {
        "code": "NTF-00005",
        "rule_code": "RULE-00005",
        "entity_type": "request",
        "event_type": "request_reason_added",
        "recipient_scope": VISIBILITY_INTERNAL,
        "channel": "inbox",
        "template_key": "request_blocker_internal",
        "min_interval_seconds": 1800,
        "metadata_json": {"reason_kind_in": ["blocker"]},
    },
]

BASELINE_ESCALATION_HINTS: list[dict[str, Any]] = [
    {
        "code": "SLA-00001",
        "entity_type": "request",
        "status_code": "needs_review",
        "severity": "warning",
        "sla_minutes": 240,
        "overdue_after_minutes": 480,
        "dashboard_bucket": "processing_requests",
        "metadata_json": {"label": "Первичный review заявки"},
    },
    {
        "code": "SLA-00002",
        "entity_type": "offer",
        "status_code": "sent",
        "severity": "warning",
        "sla_minutes": 1440,
        "overdue_after_minutes": 2880,
        "dashboard_bucket": "offers_pending_confirmation",
        "metadata_json": {"label": "Ожидание подтверждения предложения"},
    },
    {
        "code": "SLA-00003",
        "entity_type": "order",
        "status_code": "in_production",
        "severity": "critical",
        "sla_minutes": 1440,
        "overdue_after_minutes": 2880,
        "dashboard_bucket": "orders_processing",
        "metadata_json": {"label": "Производственный прогресс заказа"},
    },
]


class RuleViolation(Exception):
    def __init__(self, detail: str, *, explainability: dict[str, Any], status_code: int = 409):
        super().__init__(detail)
        self.detail = detail
        self.explainability = explainability
        self.status_code = status_code


@dataclass(slots=True)
class RuleEvaluation:
    scope: str
    allowed: bool
    detail: str | None
    explainability: dict[str, Any]
    status_code: int = 409

    def raise_if_blocked(self) -> None:
        if not self.allowed and self.detail:
            raise RuleViolation(self.detail, explainability=self.explainability, status_code=self.status_code)


def normalize_visibility_scope(scope: str | None) -> str:
    if scope in {VISIBILITY_PUBLIC, VISIBILITY_INTERNAL, VISIBILITY_CUSTOMER, VISIBILITY_SUPPLIER}:
        return str(scope)
    if scope == "role":
        return VISIBILITY_INTERNAL
    return VISIBILITY_INTERNAL


def visibility_scopes_for_audience(audience: str) -> set[str]:
    if audience in {ROLE_ADMIN, ROLE_OPERATOR, VISIBILITY_INTERNAL}:
        return {VISIBILITY_PUBLIC, VISIBILITY_CUSTOMER, VISIBILITY_SUPPLIER, VISIBILITY_INTERNAL}
    if audience in {ROLE_CUSTOMER, VISIBILITY_CUSTOMER}:
        return {VISIBILITY_PUBLIC, VISIBILITY_CUSTOMER}
    if audience in {VISIBILITY_SUPPLIER, "supplier"}:
        return {VISIBILITY_PUBLIC, VISIBILITY_SUPPLIER}
    return {VISIBILITY_PUBLIC}


def _checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _humanize_reason_code(reason_code: str | None) -> str | None:
    if not reason_code:
        return None
    return reason_code.replace("_", " ").replace("-", " ").strip().capitalize()


class WorkflowSupportService:
    def __init__(self, session: Session):
        self.session = session

    def ensure_baseline_reference_data(self, *, created_by_user_id: str | None = None) -> None:
        for payload in BASELINE_REASON_CODES:
            item = self.session.scalar(select(ReasonCodeCatalog).where(ReasonCodeCatalog.code == payload["code"]))
            if item is None:
                item = ReasonCodeCatalog(code=payload["code"])
                self.session.add(item)
            item.title = payload["title"]
            item.category = payload["category"]
            item.severity = payload["severity"]
            item.default_visibility_scope = payload["default_visibility_scope"]
            item.description = payload.get("description")
            item.metadata_json = payload.get("metadata_json")
            item.is_active = True

        rule_by_code: dict[str, RuleDefinition] = {}
        for payload in BASELINE_RULES:
            rule = self.session.scalar(select(RuleDefinition).where(RuleDefinition.code == payload["code"]))
            if rule is None:
                rule = RuleDefinition(code=payload["code"])
                self.session.add(rule)
            rule.name = payload["name"]
            rule.scope = payload["scope"]
            rule.rule_kind = payload["rule_kind"]
            rule.enabled = True
            rule.description = payload["description"]
            rule.config_json = payload["config_json"]
            rule.metadata_json = payload["metadata_json"]
            rule.latest_version_no = max(int(rule.latest_version_no or 0), int(payload["version"]["version_no"]))
            # RU: version lookup делаем только после заполнения обязательных полей rule и безопасного flush.
            self.session.flush()
            rule_by_code[rule.code] = rule

            version = self.session.scalar(
                select(RuleVersion).where(
                    RuleVersion.rule_definition_id == rule.id,
                    RuleVersion.version_no == payload["version"]["version_no"],
                    RuleVersion.deleted_at.is_(None),
                )
            )
            checksum_payload = {
                "rule": payload["config_json"],
                "metadata": payload["version"]["metadata_json"],
                "explainability": payload["version"]["explainability_json"],
            }
            if version is None:
                version = RuleVersion(
                    code=reserve_code(self.session, "rules_engine_rule_versions", "RLV"),
                    rule_definition_id=rule.id,
                    version_no=payload["version"]["version_no"],
                )
                self.session.add(version)
            version.version_status = payload["version"]["version_status"]
            version.checksum = _checksum(checksum_payload)
            version.metadata_json = payload["version"]["metadata_json"]
            version.explainability_json = payload["version"]["explainability_json"]
            version.created_by_user_id = created_by_user_id

        for payload in BASELINE_NOTIFICATION_RULES:
            rule = rule_by_code[payload["rule_code"]]
            version = self.session.scalar(
                select(RuleVersion)
                .where(RuleVersion.rule_definition_id == rule.id, RuleVersion.version_no == rule.latest_version_no)
                .order_by(desc(RuleVersion.version_no))
            )
            item = self.session.scalar(select(NotificationRule).where(NotificationRule.code == payload["code"]))
            if item is None:
                item = NotificationRule(code=payload["code"])
                self.session.add(item)
            item.rule_definition_id = rule.id
            item.rule_version_id = version.id if version else None
            item.event_type = payload["event_type"]
            item.entity_type = payload["entity_type"]
            item.recipient_scope = payload["recipient_scope"]
            item.channel = payload["channel"]
            item.template_key = payload["template_key"]
            item.min_interval_seconds = int(payload["min_interval_seconds"])
            item.enabled = True
            item.metadata_json = payload.get("metadata_json")

        for payload in BASELINE_ESCALATION_HINTS:
            item = self.session.scalar(select(EscalationHint).where(EscalationHint.code == payload["code"]))
            if item is None:
                item = EscalationHint(code=payload["code"])
                self.session.add(item)
            item.entity_type = payload["entity_type"]
            item.status_code = payload.get("status_code")
            item.reason_code = payload.get("reason_code")
            item.severity = payload["severity"]
            item.sla_minutes = payload.get("sla_minutes")
            item.overdue_after_minutes = payload.get("overdue_after_minutes")
            item.dashboard_bucket = payload["dashboard_bucket"]
            item.enabled = True
            item.metadata_json = payload.get("metadata_json")

        self.session.flush()

    def reason_catalog_map(self, codes: list[str | None]) -> dict[str, ReasonCodeCatalog]:
        actual_codes = sorted({code for code in codes if code})
        if not actual_codes:
            return {}
        items = self.session.scalars(
            select(ReasonCodeCatalog).where(ReasonCodeCatalog.code.in_(actual_codes), ReasonCodeCatalog.deleted_at.is_(None))
        ).all()
        return {item.code: item for item in items}

    def reason_display(self, reason_code: str | None) -> dict[str, Any] | None:
        if not reason_code:
            return None
        item = self.session.scalar(
            select(ReasonCodeCatalog).where(ReasonCodeCatalog.code == reason_code, ReasonCodeCatalog.deleted_at.is_(None))
        )
        if item is None:
            return {
                "code": reason_code,
                "title": _humanize_reason_code(reason_code),
                "category": "unknown",
                "severity": "info",
                "default_visibility_scope": VISIBILITY_INTERNAL,
                "description": None,
            }
        return {
            "code": item.code,
            "title": item.title,
            "category": item.category,
            "severity": item.severity,
            "default_visibility_scope": item.default_visibility_scope,
            "description": item.description,
        }

    def resolve_owner_id(self, owner_type: str, owner_code: str) -> str:
        normalized_owner_type = owner_type.lower()
        model = KEY_OBJECT_MODELS.get(normalized_owner_type)
        if model is None:
            raise LookupError("timeline_owner_type_not_supported")
        if normalized_owner_type == "request":
            item = self.session.scalar(
                select(RequestRecord).where(
                    or_(RequestRecord.code == owner_code, RequestRecord.customer_ref == owner_code),
                    RequestRecord.deleted_at.is_(None),
                )
            )
        else:
            item = self.session.scalar(select(model).where(model.code == owner_code, model.deleted_at.is_(None)))
        if item is None:
            raise LookupError("timeline_owner_not_found")
        return str(item.id)

    def _latest_rule_bundle(self, scope: str) -> tuple[RuleDefinition | None, RuleVersion | None]:
        rule = self.session.scalar(
            select(RuleDefinition).where(RuleDefinition.scope == scope, RuleDefinition.deleted_at.is_(None)).order_by(desc(RuleDefinition.updated_at))
        )
        if rule is None:
            return None, None
        version = self.session.scalar(
            select(RuleVersion)
            .where(
                RuleVersion.rule_definition_id == rule.id,
                RuleVersion.version_no == rule.latest_version_no,
                RuleVersion.deleted_at.is_(None),
            )
            .order_by(desc(RuleVersion.version_no))
        )
        return rule, version

    def _evaluation_payload(
        self,
        *,
        scope: str,
        allowed: bool,
        checks: list[dict[str, Any]],
        blockers: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        rule, version = self._latest_rule_bundle(scope)
        return {
            "scope": scope,
            "allowed": allowed,
            "rule": {
                "code": rule.code if rule else None,
                "name": rule.name if rule else None,
                "rule_kind": rule.rule_kind if rule else None,
                "latest_version_no": rule.latest_version_no if rule else None,
            },
            "version": {
                "code": version.code if version else None,
                "version_no": version.version_no if version else None,
                "version_status": version.version_status if version else None,
                "metadata": dict(version.metadata_json or {}) if version else {},
                "explainability": dict(version.explainability_json or {}) if version else {},
            },
            "checks": checks,
            "blockers": blockers,
            "context": context,
        }

    def evaluate_draft_submit(self, *, draft, snapshot, file_links: list[Any]) -> RuleEvaluation:
        checks = []
        for field_name in ["customer_email", "title", "summary", "item_service_context", "city", "requested_deadline_at"]:
            value = getattr(draft, field_name, None)
            status = "passed" if value else "failed"
            checks.append({"check": f"required_field:{field_name}", "status": status, "message": field_name})
        checks.append({"check": "file_requirement", "status": "passed", "message": "file_optional" if not file_links else "files_present"})
        blockers = []
        if not snapshot.ready_to_submit:
            blockers.append(
                {
                    "reason_code": "draft_required_fields_missing",
                    "reason_display": self.reason_display("draft_required_fields_missing"),
                    "details": {"missing_fields": list(snapshot.missing_fields)},
                }
            )
        payload = self._evaluation_payload(
            scope="drafts_requests.submit",
            allowed=snapshot.ready_to_submit,
            checks=checks,
            blockers=blockers,
            context={"draft_code": draft.code, "draft_status": draft.draft_status, "missing_fields": list(snapshot.missing_fields)},
        )
        return RuleEvaluation(
            scope="drafts_requests.submit",
            allowed=snapshot.ready_to_submit,
            detail=None if snapshot.ready_to_submit else "draft_required_fields_missing",
            explainability=payload,
            status_code=422,
        )

    def evaluate_request_transition(
        self,
        *,
        request,
        target_status: str,
        allowed_targets: set[str],
        active_blockers: list[Any],
    ) -> RuleEvaluation:
        checks = [
            {
                "check": "transition_graph",
                "status": "passed" if target_status in allowed_targets else "failed",
                "message": f"{request.request_status}->{target_status}",
            },
            {
                "check": "active_blockers",
                "status": "failed" if active_blockers and target_status not in {"needs_clarification", "cancelled"} else "passed",
                "message": f"count={len(active_blockers)}",
            },
        ]
        blockers: list[dict[str, Any]] = []
        detail = None
        status_code = 409
        if target_status not in allowed_targets:
            detail = "request_transition_not_allowed"
            blockers.append({"reason_code": detail, "reason_display": self.reason_display(detail)})
        elif active_blockers and target_status not in {"needs_clarification", "cancelled"}:
            detail = "request_has_active_blockers"
            blockers.append(
                {
                    "reason_code": detail,
                    "reason_display": self.reason_display(detail),
                    "details": {"active_blockers": [item.reason_code for item in active_blockers]},
                }
            )
        payload = self._evaluation_payload(
            scope="drafts_requests.transition",
            allowed=detail is None,
            checks=checks,
            blockers=blockers,
            context={
                "request_code": request.code,
                "request_status": request.request_status,
                "target_status": target_status,
                "active_blocker_count": len(active_blockers),
            },
        )
        return RuleEvaluation(
            scope="drafts_requests.transition",
            allowed=detail is None,
            detail=detail,
            explainability=payload,
            status_code=status_code,
        )

    def evaluate_offer_to_order(self, *, offer, version, request, existing_order: bool) -> RuleEvaluation:
        checks = [
            {"check": "confirmation_state", "status": "passed" if version.confirmation_state == "accepted" else "failed", "message": version.confirmation_state},
            {"check": "request_status", "status": "passed" if request.request_status == "offer_sent" else "failed", "message": request.request_status},
            {"check": "existing_order_guard", "status": "passed" if not existing_order else "failed", "message": "existing_order" if existing_order else "clear"},
        ]
        blockers: list[dict[str, Any]] = []
        detail = None
        if version.confirmation_state != "accepted":
            detail = "offer_version_not_confirmed"
        elif request.request_status != "offer_sent":
            detail = "request_transition_not_allowed"
        elif existing_order:
            detail = "order_already_exists_for_offer_version"
        if detail:
            blockers.append({"reason_code": detail, "reason_display": self.reason_display(detail)})
        payload = self._evaluation_payload(
            scope="offers.convert_to_order",
            allowed=detail is None,
            checks=checks,
            blockers=blockers,
            context={
                "offer_code": offer.code,
                "offer_status": offer.offer_status,
                "confirmation_state": version.confirmation_state,
                "request_status": request.request_status,
            },
        )
        return RuleEvaluation(scope="offers.convert_to_order", allowed=detail is None, detail=detail, explainability=payload)

    def evaluate_order_action(
        self,
        *,
        order,
        action: str,
        supplier_assigned: bool,
        readiness_state: str,
        logistics_state: str,
    ) -> RuleEvaluation:
        checks = [
            {"check": "supplier_assignment", "status": "passed" if supplier_assigned else "failed", "message": "supplier_ready" if supplier_assigned else "supplier_missing"},
            {"check": "readiness_state", "status": "passed", "message": readiness_state},
            {"check": "logistics_state", "status": "passed", "message": logistics_state},
        ]
        detail = None
        if action == "confirm_start" and not supplier_assigned:
            detail = "supplier_assignment_required"
        elif action == "mark_production" and order.order_status not in {"confirmed_start", "supplier_assigned", "in_production", "partially_ready"}:
            detail = "order_not_ready_for_production"
        elif action == "ready" and order.order_status not in {"confirmed_start", "in_production", "supplier_assigned", "partially_ready"}:
            detail = "order_not_ready_for_readiness_update"
        elif action == "delivery" and readiness_state not in {"ready", "partial_ready"}:
            detail = "order_not_ready_for_delivery"
        elif action == "complete" and logistics_state not in {"delivered", "partial_delivery"}:
            detail = "order_not_ready_for_completion"
        blockers = [{"reason_code": detail, "reason_display": self.reason_display(detail)}] if detail else []
        payload = self._evaluation_payload(
            scope="orders.critical_action",
            allowed=detail is None,
            checks=checks,
            blockers=blockers,
            context={
                "order_code": order.code,
                "order_status": order.order_status,
                "action": action,
                "readiness_state": readiness_state,
                "logistics_state": logistics_state,
            },
        )
        return RuleEvaluation(scope="orders.critical_action", allowed=detail is None, detail=detail, explainability=payload)

    def _notification_rules_query(self, event: MessageEvent) -> Select[tuple[NotificationRule]]:
        return (
            select(NotificationRule)
            .where(
                NotificationRule.enabled.is_(True),
                NotificationRule.deleted_at.is_(None),
                NotificationRule.entity_type == event.owner_type,
                NotificationRule.event_type == event.event_type,
            )
            .order_by(NotificationRule.created_at.asc())
        )

    def _notification_matches(self, rule: NotificationRule, event: MessageEvent) -> bool:
        metadata = dict(rule.metadata_json or {})
        event_payload = dict(event.payload_json or {})
        status_in = metadata.get("status_in")
        if status_in and event_payload.get("target_status") not in set(status_in):
            return False
        reason_kind_in = metadata.get("reason_kind_in")
        if reason_kind_in and event_payload.get("reason_kind") not in set(reason_kind_in):
            return False
        return True

    def _render_notification(self, rule: NotificationRule, event: MessageEvent) -> tuple[str, str]:
        reason_display = self.reason_display(event.reason_code)
        payload = dict(event.payload_json or {})
        owner_code = payload.get("entity_code") or payload.get("request_code") or payload.get("offer_code") or payload.get("order_code")
        if rule.template_key == "request_clarification_needed":
            return "Нужно уточнение по заявке", f"Заявка {owner_code or ''} переведена в режим уточнения. Проверь список follow-up и причин."
        if rule.template_key == "offer_sent_customer":
            return "Предложение отправлено", f"Для объекта {owner_code or event.owner_type} отправлена новая версия предложения."
        if rule.template_key == "order_created_internal":
            return "Создан новый заказ", f"Заказ по подтверждённому предложению создан и ждёт дальнейших действий."
        if rule.template_key == "document_sent_customer":
            return "Документ отправлен", f"Для твоего кейса опубликован и отправлен актуальный документ."
        if rule.template_key == "request_blocker_internal":
            return "Новый blocker по заявке", f"Появился blocker: {reason_display['title'] if reason_display else event.reason_code}."
        fallback = reason_display["title"] if reason_display else _humanize_reason_code(event.reason_code)
        return fallback or "Новое событие", f"Зафиксировано событие {event.event_type} по объекту {owner_code or event.owner_type}."

    def emit_message_event_from_audit(self, audit_event: AuditEvent) -> MessageEvent:
        owner_type = {
            "supplier_company": "supplier",
            "file_asset": "file",
        }.get(audit_event.entity_type, audit_event.entity_type)
        visibility_scope = normalize_visibility_scope(audit_event.visibility)
        payload = dict(audit_event.payload_json or {})
        payload.setdefault("entity_type", audit_event.entity_type)
        payload.setdefault("entity_code", audit_event.entity_code)
        payload.setdefault("request_id", audit_event.request_id)
        item = MessageEvent(
            code=reserve_code(self.session, "message_events", "MSG"),
            owner_type=owner_type,
            owner_id=audit_event.entity_id,
            entry_kind="event",
            channel="system",
            actor_type="user" if audit_event.actor_user_id else "system",
            actor_user_id=audit_event.actor_user_id,
            actor_role=audit_event.actor_role,
            event_type=audit_event.action,
            message_type="audit_event",
            visibility_scope=visibility_scope,
            reason_code=audit_event.reason,
            title=_humanize_reason_code(audit_event.action),
            body=self.reason_display(audit_event.reason)["title"] if audit_event.reason else None,
            payload_json=payload,
            occurred_at=audit_event.created_at,
            source_audit_event_id=audit_event.id,
        )
        self.session.add(item)
        self.session.flush()
        self.process_notification_rules(item)
        return item

    def process_notification_rules(self, event: MessageEvent) -> list[MessageEvent]:
        if event.entry_kind != "event":
            return []
        created: list[MessageEvent] = []
        for rule in self.session.scalars(self._notification_rules_query(event)).all():
            if not self._notification_matches(rule, event):
                continue
            dedupe_key = f"{rule.code}:{event.owner_type}:{event.owner_id}:{event.event_type}:{event.reason_code or ''}"
            if rule.min_interval_seconds > 0:
                threshold = utc_now() - timedelta(seconds=rule.min_interval_seconds)
                existing = self.session.scalar(
                    select(MessageEvent).where(
                        MessageEvent.entry_kind == "notification",
                        MessageEvent.dedupe_key == dedupe_key,
                        MessageEvent.deleted_at.is_(None),
                        MessageEvent.created_at >= threshold,
                    )
                )
                if existing is not None:
                    continue
            title, body = self._render_notification(rule, event)
            item = MessageEvent(
                code=reserve_code(self.session, "message_events", "MSG"),
                owner_type=event.owner_type,
                owner_id=event.owner_id,
                entry_kind="notification",
                channel=rule.channel,
                actor_type="system",
                actor_role="system",
                event_type=event.event_type,
                message_type=rule.template_key,
                visibility_scope=normalize_visibility_scope(rule.recipient_scope),
                reason_code=event.reason_code,
                title=title,
                body=body,
                dedupe_key=dedupe_key,
                payload_json={
                    "rule_code": rule.code,
                    "rule_version_id": rule.rule_version_id,
                    "source_message_code": event.code,
                    "source_audit_event_id": event.source_audit_event_id,
                    **dict(event.payload_json or {}),
                },
                occurred_at=event.occurred_at,
                parent_message_id=event.id,
            )
            self.session.add(item)
            self.session.flush()
            created.append(item)
        return created

    def list_timeline(self, *, owner_type: str, owner_id: str, audience: str) -> list[MessageEvent]:
        scopes = visibility_scopes_for_audience(audience)
        return self.session.scalars(
            select(MessageEvent)
            .where(
                MessageEvent.owner_type == owner_type,
                MessageEvent.owner_id == owner_id,
                MessageEvent.deleted_at.is_(None),
                MessageEvent.visibility_scope.in_(scopes),
            )
            .order_by(MessageEvent.occurred_at.asc(), MessageEvent.created_at.asc())
        ).all()

    def list_recent_notifications(self, *, audience: str, limit: int = 20) -> list[MessageEvent]:
        scopes = visibility_scopes_for_audience(audience)
        return self.session.scalars(
            select(MessageEvent)
            .where(
                MessageEvent.entry_kind == "notification",
                MessageEvent.deleted_at.is_(None),
                MessageEvent.visibility_scope.in_(scopes),
            )
            .order_by(desc(MessageEvent.occurred_at), desc(MessageEvent.created_at))
            .limit(limit)
        ).all()
