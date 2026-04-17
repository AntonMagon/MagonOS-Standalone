# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit_event
from ..codes import reserve_code
from ..dependencies import get_db, require_roles
from ..models import RuleDefinition, RuleVersion
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext

router = APIRouter(tags=["RulesEngine"])


class RuleCreatePayload(BaseModel):
    name: str = Field(min_length=2)
    scope: str = Field(min_length=2)
    description: str | None = None
    enabled: bool = True
    config_json: dict | None = None


@router.get("/api/v1/operator/rules")
def list_rules(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(select(RuleDefinition).order_by(RuleDefinition.created_at.asc())).all()
    return {
        "items": [
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "scope": item.scope,
                "rule_kind": item.rule_kind,
                "latest_version_no": item.latest_version_no,
                "enabled": item.enabled,
                "metadata": dict(item.metadata_json or {}),
            }
            for item in items
        ]
    }


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
        rule_kind="transition_guard",
        description=payload.description,
        enabled=payload.enabled,
        config_json=payload.config_json,
        latest_version_no=1,
    )
    session.add(item)
    session.flush()
    session.add(
        RuleVersion(
            code=reserve_code(session, "rules_engine_rule_versions", "RLV"),
            rule_definition_id=item.id,
            version_no=1,
            version_status="active",
            metadata_json={"created_via": "admin_api"},
            explainability_json={"summary": payload.description or payload.name},
            created_by_user_id=auth.user_id,
        )
    )
    session.flush()
    record_audit_event(session, module_name="rules_engine", action="rule_created", entity_type="rule", entity_id=item.id, entity_code=item.code, auth=auth, reason="admin_create_rule", payload_json={"scope": item.scope})
    return {"item": {"id": item.id, "code": item.code, "scope": item.scope}}
