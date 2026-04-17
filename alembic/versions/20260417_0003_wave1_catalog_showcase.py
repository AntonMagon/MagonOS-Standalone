"""wave1 catalog showcase

Revision ID: 20260417_0003
Revises: 20260417_0002
Create Date: 2026-04-17 16:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0003"
down_revision = "20260417_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    op.add_column("catalog_items", sa.Column("supplier_company_id", sa.String(length=36), nullable=True))
    op.add_column("catalog_items", sa.Column("category_code", sa.String(length=64), nullable=False, server_default="general"))
    op.add_column("catalog_items", sa.Column("category_label", sa.String(length=255), nullable=False, server_default="General"))
    op.add_column("catalog_items", sa.Column("tags_json", sa.JSON(), nullable=True))
    op.add_column("catalog_items", sa.Column("option_summaries_json", sa.JSON(), nullable=True))
    op.add_column("catalog_items", sa.Column("pricing_mode", sa.String(length=32), nullable=False, server_default="estimate"))
    op.add_column("catalog_items", sa.Column("pricing_summary", sa.Text(), nullable=True))
    op.add_column("catalog_items", sa.Column("pricing_note", sa.Text(), nullable=True))
    op.add_column("catalog_items", sa.Column("catalog_mode", sa.String(length=32), nullable=False, server_default="rfq"))
    op.add_column("catalog_items", sa.Column("translations_json", sa.JSON(), nullable=True))
    op.add_column("catalog_items", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("catalog_items", sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.true()))
    if dialect != "sqlite":
        op.create_foreign_key("fk_catalog_items_supplier_company", "catalog_items", "supplier_companies", ["supplier_company_id"], ["id"])

    op.add_column("draft_requests", sa.Column("catalog_item_id", sa.String(length=36), nullable=True))
    op.add_column("draft_requests", sa.Column("customer_phone", sa.String(length=64), nullable=True))
    op.add_column("draft_requests", sa.Column("guest_company_name", sa.String(length=255), nullable=True))
    op.add_column("draft_requests", sa.Column("locale_code", sa.String(length=8), nullable=False, server_default="ru"))
    if dialect != "sqlite":
        op.create_foreign_key("fk_draft_requests_catalog_item", "draft_requests", "catalog_items", ["catalog_item_id"], ["id"])

    op.add_column("requests", sa.Column("catalog_item_id", sa.String(length=36), nullable=True))
    op.add_column("requests", sa.Column("customer_name", sa.String(length=255), nullable=True))
    op.add_column("requests", sa.Column("customer_phone", sa.String(length=64), nullable=True))
    op.add_column("requests", sa.Column("guest_company_name", sa.String(length=255), nullable=True))
    op.add_column("requests", sa.Column("locale_code", sa.String(length=8), nullable=False, server_default="ru"))
    if dialect != "sqlite":
        op.create_foreign_key("fk_requests_catalog_item", "requests", "catalog_items", ["catalog_item_id"], ["id"])

    if dialect != "sqlite":
        op.alter_column("catalog_items", "category_code", server_default=None)
        op.alter_column("catalog_items", "category_label", server_default=None)
        op.alter_column("catalog_items", "pricing_mode", server_default=None)
        op.alter_column("catalog_items", "catalog_mode", server_default=None)
        op.alter_column("catalog_items", "sort_order", server_default=None)
        op.alter_column("draft_requests", "locale_code", server_default=None)
        op.alter_column("requests", "locale_code", server_default=None)


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "sqlite":
        op.drop_constraint("fk_requests_catalog_item", "requests", type_="foreignkey")
    op.drop_column("requests", "locale_code")
    op.drop_column("requests", "guest_company_name")
    op.drop_column("requests", "customer_phone")
    op.drop_column("requests", "customer_name")
    op.drop_column("requests", "catalog_item_id")

    if dialect != "sqlite":
        op.drop_constraint("fk_draft_requests_catalog_item", "draft_requests", type_="foreignkey")
    op.drop_column("draft_requests", "locale_code")
    op.drop_column("draft_requests", "guest_company_name")
    op.drop_column("draft_requests", "customer_phone")
    op.drop_column("draft_requests", "catalog_item_id")

    if dialect != "sqlite":
        op.drop_constraint("fk_catalog_items_supplier_company", "catalog_items", type_="foreignkey")
    op.drop_column("catalog_items", "is_featured")
    op.drop_column("catalog_items", "sort_order")
    op.drop_column("catalog_items", "translations_json")
    op.drop_column("catalog_items", "catalog_mode")
    op.drop_column("catalog_items", "pricing_note")
    op.drop_column("catalog_items", "pricing_summary")
    op.drop_column("catalog_items", "pricing_mode")
    op.drop_column("catalog_items", "option_summaries_json")
    op.drop_column("catalog_items", "tags_json")
    op.drop_column("catalog_items", "category_label")
    op.drop_column("catalog_items", "category_code")
    op.drop_column("catalog_items", "supplier_company_id")
