# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit_event
from ..codes import reserve_code
from ..dependencies import get_db, require_roles
from ..models import Company
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from .shared import company_operator_view, company_public_view

router = APIRouter(tags=["Companies"])


class CompanyCreatePayload(BaseModel):
    public_name: str = Field(min_length=2)
    legal_name: str | None = None
    country_code: str = "VN"
    public_note: str | None = None
    internal_note: str | None = None


@router.get("/api/v1/public/companies")
def public_companies(session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(select(Company).where(Company.deleted_at.is_(None)).order_by(Company.created_at.asc())).all()
    return {"items": [company_public_view(item) for item in items]}


@router.get("/api/v1/operator/companies")
def operator_companies(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(select(Company).order_by(Company.created_at.asc())).all()
    return {"items": [company_operator_view(item) for item in items]}


@router.post("/api/v1/admin/companies")
def create_company(payload: CompanyCreatePayload, auth: AuthContext = Depends(require_roles(ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    company = Company(
        code=reserve_code(session, "companies", "CMP"),
        public_name=payload.public_name,
        legal_name=payload.legal_name,
        country_code=payload.country_code,
        public_status="active",
        internal_status="prospect",
        public_note=payload.public_note,
        internal_note=payload.internal_note,
    )
    session.add(company)
    session.flush()
    record_audit_event(
        session,
        module_name="companies",
        action="create",
        entity_type="company",
        entity_id=company.id,
        entity_code=company.code,
        auth=auth,
        reason="admin_create_company",
        payload_json={"public_name": company.public_name},
    )
    return {"item": company_operator_view(company)}
