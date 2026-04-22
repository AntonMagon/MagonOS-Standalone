# RU: Файл входит в проверенный контур первой волны.
# RU: Базовая настройка правил теперь живёт не только в сид-данных, но и в admin configuration contour.
from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit_event
from ..codes import reserve_code
from ..dependencies import get_db, require_roles
from ..models import NotificationRule, RuleDefinition, RuleVersion
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext

router = APIRouter(tags=["RulesEngine"])


class RuleCreatePayload(BaseModel):
    name: str = Field(min_length=2)
    scope: str = Field(min_length=2)
    rule_kind: str = "transition_guard"
    description: str | None = None
    enabled: bool = True
    config_json: dict | None = None
    metadata_json: dict | None = None
    explainability_json: dict | None = None


class RuleUpdatePayload(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    scope: str | None = Field(default=None, min_length=2)
    rule_kind: str | None = None
    description: str | None = None
    enabled: bool | None = None
    config_json: dict | None = None
    metadata_json: dict | None = None


class RuleVersionCreatePayload(BaseModel):
    version_status: str = "active"
    metadata_json: dict | None = None
    explainability_json: dict | None = None
    effective_to: str | None = None


class NotificationRuleCreatePayload(BaseModel):
    event_type: str = Field(min_length=2)
    entity_type: str = Field(min_length=2)
    recipient_scope: str = "internal"
    channel: str = "inbox"
    template_key: str = Field(min_length=2)
    min_interval_seconds: int = 0
    enabled: bool = True
    rule_code: str | None = None
    metadata_json: dict | None = None


class NotificationRuleUpdatePayload(BaseModel):
    event_type: str | None = Field(default=None, min_length=2)
    entity_type: str | None = Field(default=None, min_length=2)
    recipient_scope: str | None = None
    channel: str | None = None
    template_key: str | None = Field(default=None, min_length=2)
    min_interval_seconds: int | None = None
    enabled: bool | None = None
    rule_code: str | None = None
    metadata_json: dict | None = None


def _rule_view(item: RuleDefinition) -> dict[str, object]:
    return {
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "scope": item.scope,
        "rule_kind": item.rule_kind,
        "latest_version_no": item.latest_version_no,
        "enabled": item.enabled,
        "description": item.description,
        "config_json": dict(item.config_json or {}),
        "metadata_json": dict(item.metadata_json or {}),
    }


def _notification_rule_view(item: NotificationRule, rule: RuleDefinition | None = None) -> dict[str, object]:
    return {
        "code": item.code,
        "event_type": item.event_type,
        "entity_type": item.entity_type,
        "recipient_scope": item.recipient_scope,
        "channel": item.channel,
        "template_key": item.template_key,
        "min_interval_seconds": item.min_interval_seconds,
        "enabled": item.enabled,
        "rule_code": rule.code if rule else None,
        "metadata_json": dict(item.metadata_json or {}),
    }


def _latest_rule_version(session: Session, rule: RuleDefinition) -> RuleVersion | None:
    return session.scalar(
        select(RuleVersion)
        .where(RuleVersion.rule_definition_id == rule.id, RuleVersion.deleted_at.is_(None))
        .order_by(RuleVersion.version_no.desc())
    )


@router.get("/api/v1/operator/rules")
def list_rules(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(select(RuleDefinition).order_by(RuleDefinition.created_at.asc())).all()
    return {"items": [_rule_view(item) for item in items]}


@router.get("/api/v1/operator/rules/{rule_code}/versions")
def list_rule_versions(rule_code: str, _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    rule = session.scalar(select(RuleDefinition).where(RuleDefinition.code == rule_code, RuleDefinition.deleted_at.is_(None)))
    if rule is None:
        raise HTTPException(status_code=404, detail="rule_not_found")
    items = session.scalars(
        select(RuleVersion)
        .where(RuleVersion.rule_definition_id == rule.id, RuleVersion.deleted_at.is_(None))
        .order_by(RuleVersion.version_no.desc())
    ).all()
    return {
        "rule": {
            "code": rule.code,
            "name": rule.name,
            "scope": rule.scope,
            "rule_kind": rule.rule_kind,
            "latest_version_no": rule.latest_version_no,
        },
        "items": [
            {
                "code": item.code,
                "version_no": item.version_no,
                "version_status": item.version_status,
                "checksum": item.checksum,
                "metadata": dict(item.metadata_json or {}),
                "explainability": dict(item.explainability_json or {}),
                "effective_from": item.effective_from.isoformat() if item.effective_from else None,
                "effective_to": item.effective_to.isoformat() if item.effective_to else None,
            }
            for item in items
        ],
    }


@router.post("/api/v1/admin/rules")
def create_rule(payload: RuleCreatePayload, auth: AuthContext = Depends(require_roles(ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    item = RuleDefinition(
        code=reserve_code(session, "rules_engine_rules", "RUL"),
        name=payload.name,
        scope=payload.scope,
        rule_kind=payload.rule_kind,
        description=payload.description,
        enabled=payload.enabled,
        config_json=payload.config_json,
        metadata_json=payload.metadata_json or {},
        latest_version_no=1,
    )
    session.add(item)
    session.flush()
    version_metadata = {"created_via": "admin_api", **dict(payload.metadata_json or {})}
    version_explainability = payload.explainability_json or {"summary": payload.description or payload.name}
    checksum_payload = {
        "name": item.name,
        "scope": item.scope,
        "rule_kind": item.rule_kind,
        "config_json": item.config_json or {},
        "metadata_json": version_metadata,
        "explainability_json": version_explainability,
    }
    session.add(
        RuleVersion(
            code=reserve_code(session, "rules_engine_rule_versions", "RLV"),
            rule_definition_id=item.id,
            version_no=1,
            version_status="active",
            checksum=hashlib.sha256(json.dumps(checksum_payload, sort_keys=True).encode("utf-8")).hexdigest(),
            metadata_json=version_metadata,
            explainability_json=version_explainability,
            created_by_user_id=auth.user_id,
        )
    )
    session.flush()
    record_audit_event(session, module_name="rules_engine", action="rule_created", entity_type="rule", entity_id=item.id, entity_code=item.code, auth=auth, reason="admin_create_rule", payload_json={"scope": item.scope})
    return {"item": _rule_view(item)}


@router.patch("/api/v1/admin/rules/{rule_code}")
def update_rule(
    rule_code: str,
    payload: RuleUpdatePayload,
    auth: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    item = session.scalar(select(RuleDefinition).where(RuleDefinition.code == rule_code, RuleDefinition.deleted_at.is_(None)))
    if item is None:
        raise HTTPException(status_code=404, detail="rule_not_found")
    changed: dict[str, object] = {}
    for field_name in ("name", "scope", "rule_kind", "description", "enabled"):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(item, field_name, value)
            changed[field_name] = value
    if payload.config_json is not None:
        item.config_json = payload.config_json
        changed["config_json"] = payload.config_json
    if payload.metadata_json is not None:
        item.metadata_json = payload.metadata_json
        changed["metadata_json"] = payload.metadata_json
    session.flush()
    record_audit_event(
        session,
        module_name="rules_engine",
        action="rule_updated",
        entity_type="rule",
        entity_id=item.id,
        entity_code=item.code,
        auth=auth,
        reason="admin_update_rule",
        payload_json=changed,
    )
    return {"item": _rule_view(item)}


@router.post("/api/v1/admin/rules/{rule_code}/versions")
def create_rule_version(
    rule_code: str,
    payload: RuleVersionCreatePayload,
    auth: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    rule = session.scalar(select(RuleDefinition).where(RuleDefinition.code == rule_code, RuleDefinition.deleted_at.is_(None)))
    if rule is None:
        raise HTTPException(status_code=404, detail="rule_not_found")
    version_no = int(rule.latest_version_no or 0) + 1
    explainability = payload.explainability_json or {"summary": rule.description or rule.name}
    metadata = payload.metadata_json or {}
    checksum_payload = {
        "rule_code": rule.code,
        "rule_kind": rule.rule_kind,
        "config_json": rule.config_json or {},
        "metadata_json": metadata,
        "explainability_json": explainability,
        "version_no": version_no,
    }
    version = RuleVersion(
        code=reserve_code(session, "rules_engine_rule_versions", "RLV"),
        rule_definition_id=rule.id,
        version_no=version_no,
        version_status=payload.version_status,
        checksum=hashlib.sha256(json.dumps(checksum_payload, sort_keys=True).encode("utf-8")).hexdigest(),
        metadata_json=metadata,
        explainability_json=explainability,
        created_by_user_id=auth.user_id,
    )
    session.add(version)
    rule.latest_version_no = version_no
    session.flush()
    record_audit_event(
        session,
        module_name="rules_engine",
        action="rule_version_created",
        entity_type="rule",
        entity_id=rule.id,
        entity_code=rule.code,
        auth=auth,
        reason="admin_create_rule_version",
        payload_json={"version_no": version_no, "version_status": payload.version_status},
    )
    return {
        "item": {
            "code": version.code,
            "version_no": version.version_no,
            "version_status": version.version_status,
            "checksum": version.checksum,
            "metadata_json": dict(version.metadata_json or {}),
            "explainability_json": dict(version.explainability_json or {}),
        }
    }


@router.get("/api/v1/admin/notification-rules")
def list_notification_rules(
    _: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    items = session.scalars(
        select(NotificationRule)
        .where(NotificationRule.deleted_at.is_(None))
        .order_by(NotificationRule.created_at.asc())
    ).all()
    rules = {
        item.id: item
        for item in session.scalars(select(RuleDefinition).where(RuleDefinition.deleted_at.is_(None))).all()
    }
    return {"items": [_notification_rule_view(item, rules.get(item.rule_definition_id)) for item in items]}


@router.post("/api/v1/admin/notification-rules")
def create_notification_rule(
    payload: NotificationRuleCreatePayload,
    auth: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    rule: RuleDefinition | None = None
    rule_version_id: str | None = None
    if payload.rule_code:
        rule = session.scalar(select(RuleDefinition).where(RuleDefinition.code == payload.rule_code, RuleDefinition.deleted_at.is_(None)))
        if rule is None:
            raise HTTPException(status_code=404, detail="rule_not_found")
        latest_version = _latest_rule_version(session, rule)
        rule_version_id = latest_version.id if latest_version else None
    item = NotificationRule(
        code=reserve_code(session, "notification_rules", "NTF"),
        rule_definition_id=rule.id if rule else None,
        rule_version_id=rule_version_id,
        event_type=payload.event_type,
        entity_type=payload.entity_type,
        recipient_scope=payload.recipient_scope,
        channel=payload.channel,
        template_key=payload.template_key,
        min_interval_seconds=payload.min_interval_seconds,
        enabled=payload.enabled,
        metadata_json=payload.metadata_json or {},
    )
    session.add(item)
    session.flush()
    record_audit_event(
        session,
        module_name="rules_engine",
        action="notification_rule_created",
        entity_type="notification_rule",
        entity_id=item.id,
        entity_code=item.code,
        auth=auth,
        reason="admin_create_notification_rule",
        payload_json={"event_type": item.event_type, "entity_type": item.entity_type, "recipient_scope": item.recipient_scope},
    )
    return {"item": _notification_rule_view(item, rule)}


@router.patch("/api/v1/admin/notification-rules/{notification_rule_code}")
def update_notification_rule(
    notification_rule_code: str,
    payload: NotificationRuleUpdatePayload,
    auth: AuthContext = Depends(require_roles(ROLE_ADMIN)),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    item = session.scalar(
        select(NotificationRule).where(NotificationRule.code == notification_rule_code, NotificationRule.deleted_at.is_(None))
    )
    if item is None:
        raise HTTPException(status_code=404, detail="notification_rule_not_found")
    linked_rule: RuleDefinition | None = None
    changed: dict[str, object] = {}
    for field_name in ("event_type", "entity_type", "recipient_scope", "channel", "template_key", "min_interval_seconds", "enabled"):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(item, field_name, value)
            changed[field_name] = value
    if payload.metadata_json is not None:
        item.metadata_json = payload.metadata_json
        changed["metadata_json"] = payload.metadata_json
    if payload.rule_code is not None:
        if payload.rule_code == "":
            item.rule_definition_id = None
            item.rule_version_id = None
            changed["rule_code"] = None
        else:
            linked_rule = session.scalar(select(RuleDefinition).where(RuleDefinition.code == payload.rule_code, RuleDefinition.deleted_at.is_(None)))
            if linked_rule is None:
                raise HTTPException(status_code=404, detail="rule_not_found")
            latest_version = _latest_rule_version(session, linked_rule)
            item.rule_definition_id = linked_rule.id
            item.rule_version_id = latest_version.id if latest_version else None
            changed["rule_code"] = linked_rule.code
    session.flush()
    record_audit_event(
        session,
        module_name="rules_engine",
        action="notification_rule_updated",
        entity_type="notification_rule",
        entity_id=item.id,
        entity_code=item.code,
        auth=auth,
        reason="admin_update_notification_rule",
        payload_json=changed,
    )
    if linked_rule is None and item.rule_definition_id:
        linked_rule = session.get(RuleDefinition, item.rule_definition_id)
    return {"item": _notification_rule_view(item, linked_rule)}
