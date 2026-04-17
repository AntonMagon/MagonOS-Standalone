from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit_event
from ..codes import reserve_code
from ..dependencies import get_db, require_roles
from ..models import CatalogItem, Supplier, SupplierCompany
from ..security import ROLE_ADMIN, ROLE_OPERATOR, AuthContext
from .shared import catalog_operator_view, catalog_public_view

router = APIRouter(tags=["Catalog"])


class CatalogCreatePayload(BaseModel):
    public_title: str = Field(min_length=2)
    supplier_code: str | None = None
    supplier_company_code: str | None = None
    public_description: str | None = None
    internal_description: str | None = None
    category_code: str = Field(min_length=2)
    category_label: str = Field(min_length=2)
    tags: list[str] = Field(default_factory=list)
    option_summaries: list[str] = Field(default_factory=list)
    list_price: float | None = None
    currency_code: str = "VND"
    pricing_mode: str = "estimate"
    pricing_summary: str | None = None
    pricing_note: str | None = None
    mode: str = "rfq"
    visibility: str = "public"
    translations: dict[str, object] | None = None
    is_featured: bool = True
    sort_order: int = 100
    reason_code: str = "catalog_manual_create"


def _public_catalog_query(session: Session):
    return session.scalars(
        select(CatalogItem)
        .where(CatalogItem.visibility == "public", CatalogItem.deleted_at.is_(None))
        .order_by(CatalogItem.sort_order.asc(), CatalogItem.created_at.asc())
    ).all()


def _normalize_catalog_payload(payload: CatalogCreatePayload) -> dict[str, object]:
    if payload.pricing_mode not in {"fixed", "from", "estimate", "rfq"}:
        raise HTTPException(status_code=422, detail="catalog_pricing_mode_invalid")
    if payload.mode not in {"ready", "config", "rfq"}:
        raise HTTPException(status_code=422, detail="catalog_mode_invalid")
    if payload.visibility not in {"public", "hidden", "internal"}:
        raise HTTPException(status_code=422, detail="catalog_visibility_invalid")
    # RU: Ограничиваем витрину curated-набором и не даём засунуть в option summary произвольный blob вместо коротких коммерчески читаемых пунктов.
    normalized_options = [item.strip() for item in payload.option_summaries if item.strip()][:6]
    normalized_tags = [item.strip() for item in payload.tags if item.strip()][:8]
    return {
        "normalized_options": normalized_options,
        "normalized_tags": normalized_tags,
    }


@router.get("/api/v1/public/catalog/directions")
def public_catalog_directions(session: Session = Depends(get_db)) -> dict[str, object]:
    items = _public_catalog_query(session)
    grouped: dict[str, dict[str, object]] = {}
    for item in items:
        bucket = grouped.setdefault(
            item.category_code,
            {
                "code": item.category_code,
                "label": item.category_label,
                "item_count": 0,
                "modes": set(),
            },
        )
        bucket["item_count"] += 1
        bucket["modes"].add(item.catalog_mode)
    directions = [
        {
            "code": value["code"],
            "label": value["label"],
            "item_count": value["item_count"],
            "modes": sorted(value["modes"]),
        }
        for value in grouped.values()
    ]
    directions.sort(key=lambda item: (item["label"], item["code"]))
    return {"items": directions}


@router.get("/api/v1/public/catalog/items")
def public_catalog(category_code: str | None = None, session: Session = Depends(get_db)) -> dict[str, object]:
    items = _public_catalog_query(session)
    if category_code:
        items = [item for item in items if item.category_code == category_code]
    return {"items": [catalog_public_view(item) for item in items]}


@router.get("/api/v1/public/catalog/items/{item_code}")
def public_catalog_detail(item_code: str, session: Session = Depends(get_db)) -> dict[str, object]:
    item = session.scalar(select(CatalogItem).where(CatalogItem.code == item_code, CatalogItem.deleted_at.is_(None)))
    if item is None or item.visibility != "public":
        raise HTTPException(status_code=404, detail="catalog_item_not_found")
    return {"item": catalog_public_view(item)}


@router.get("/api/v1/operator/catalog/items")
def operator_catalog(_: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(select(CatalogItem).order_by(CatalogItem.sort_order.asc(), CatalogItem.created_at.asc())).all()
    return {"items": [catalog_operator_view(item) for item in items]}


@router.get("/api/v1/operator/catalog/items/{item_code}")
def operator_catalog_detail(item_code: str, _: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    item = session.scalar(select(CatalogItem).where(CatalogItem.code == item_code))
    if item is None:
        raise HTTPException(status_code=404, detail="catalog_item_not_found")
    return {"item": catalog_operator_view(item)}


@router.post("/api/v1/operator/catalog/items")
def create_catalog_item(payload: CatalogCreatePayload, auth: AuthContext = Depends(require_roles(ROLE_OPERATOR, ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    normalized = _normalize_catalog_payload(payload)
    supplier = None
    if payload.supplier_code:
        supplier = session.scalar(select(Supplier).where(Supplier.code == payload.supplier_code))
        if supplier is None:
            raise HTTPException(status_code=404, detail="supplier_not_found")
    supplier_company = None
    if payload.supplier_company_code:
        supplier_company = session.scalar(select(SupplierCompany).where(SupplierCompany.code == payload.supplier_company_code))
        if supplier_company is None:
            raise HTTPException(status_code=404, detail="supplier_company_not_found")
    item = CatalogItem(
        code=reserve_code(session, "catalog_items", "CAT"),
        supplier_id=supplier.id if supplier else None,
        supplier_company_id=supplier_company.id if supplier_company else None,
        public_title=payload.public_title,
        internal_title=payload.public_title,
        public_description=payload.public_description,
        internal_description=payload.internal_description,
        category_code=payload.category_code,
        category_label=payload.category_label,
        tags_json=normalized["normalized_tags"],
        option_summaries_json=normalized["normalized_options"],
        list_price=payload.list_price,
        currency_code=payload.currency_code,
        pricing_mode=payload.pricing_mode,
        pricing_summary=payload.pricing_summary,
        pricing_note=payload.pricing_note,
        catalog_mode=payload.mode,
        visibility=payload.visibility,
        translations_json=payload.translations or {},
        is_featured=payload.is_featured,
        sort_order=payload.sort_order,
    )
    session.add(item)
    session.flush()
    record_audit_event(
        session,
        module_name="catalog",
        action="create",
        entity_type="catalog_item",
        entity_id=item.id,
        entity_code=item.code,
        auth=auth,
        reason=payload.reason_code,
        payload_json={"public_title": item.public_title, "category_code": item.category_code, "mode": item.catalog_mode},
    )
    return {"item": catalog_operator_view(item)}
