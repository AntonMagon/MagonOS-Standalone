"""wave1 orders payments

Revision ID: 20260417_0006
Revises: 20260417_0005
Create Date: 2026-04-17 22:10:00
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260417_0006"
down_revision = "20260417_0005"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column("orders", sa.Column("customer_refs_json", sa.JSON(), nullable=True))
    op.add_column("orders", sa.Column("supplier_refs_json", sa.JSON(), nullable=True))
    op.add_column("orders", sa.Column("internal_owner_user_id", sa.String(length=36), nullable=True))
    op.add_column("orders", sa.Column("payment_state", sa.String(length=32), nullable=False, server_default="created"))
    op.add_column("orders", sa.Column("logistics_state", sa.String(length=32), nullable=False, server_default="planning"))
    op.add_column("orders", sa.Column("readiness_state", sa.String(length=32), nullable=False, server_default="not_ready"))
    op.add_column("orders", sa.Column("refund_state", sa.String(length=32), nullable=False, server_default="none"))
    op.add_column("orders", sa.Column("dispute_state", sa.String(length=32), nullable=False, server_default="clear"))
    op.add_column("orders", sa.Column("last_transition_reason_code", sa.String(length=128), nullable=True))
    op.add_column("orders", sa.Column("last_transition_note", sa.Text(), nullable=True))
    if dialect != "sqlite":
        op.create_foreign_key("fk_orders_internal_owner", "orders", "users_access_users", ["internal_owner_user_id"], ["id"])

    op.create_table(
        "order_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("catalog_item_id", sa.String(length=36), nullable=True),
        sa.Column("line_type", sa.String(length=32), nullable=False, server_default="catalog_service"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False, server_default="1"),
        sa.Column("unit_label", sa.String(length=32), nullable=False, server_default="lot"),
        sa.Column("line_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default="VND"),
        sa.Column("line_status", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("planned_supplier_ref", sa.String(length=64), nullable=True),
        sa.Column("planned_stage_refs_json", sa.JSON(), nullable=True),
        sa.Column("readiness_state", sa.String(length=32), nullable=False, server_default="not_ready"),
        sa.Column("delivery_state", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("refund_state", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("dispute_state", sa.String(length=32), nullable=False, server_default="clear"),
        sa.Column("last_transition_reason_code", sa.String(length=128), nullable=True),
        sa.Column("last_transition_note", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "payment_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("payment_state", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default="VND"),
        sa.Column("payment_ref", sa.String(length=128), nullable=True),
        sa.Column("provider_ref", sa.String(length=128), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_transition_reason_code", sa.String(length=128), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "internal_ledger_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("payment_record_id", sa.String(length=36), nullable=True),
        sa.Column("entry_kind", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("entry_state", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default="VND"),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["payment_record_id"], ["payment_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    orders = list(
        bind.execute(
            sa.text(
                "SELECT orders.id, orders.code, orders.request_id, orders.offer_version_id, orders.acceptance_reason, "
                "orders.created_at, orders.updated_at, orders.order_status, "
                "requests.customer_ref, requests.customer_email, requests.customer_name, requests.customer_phone, requests.guest_company_name, "
                "requests.catalog_item_id, requests.title, requests.item_service_context, requests.owner_user_id, requests.assignee_user_id, "
                "offer_versions.amount, offer_versions.currency_code, offer_versions.supplier_ref "
                "FROM orders "
                "JOIN requests ON requests.id = orders.request_id "
                "LEFT JOIN offer_versions ON offer_versions.id = orders.offer_version_id"
            )
        ).mappings()
    )
    now = _utc_now()
    for index, row in enumerate(orders, start=1):
        supplier_refs = [row["supplier_ref"]] if row["supplier_ref"] else []
        bind.execute(
            sa.text(
                "UPDATE orders SET customer_refs_json = :customer_refs_json, supplier_refs_json = :supplier_refs_json, "
                "internal_owner_user_id = :internal_owner_user_id, payment_state = :payment_state, logistics_state = :logistics_state, "
                "readiness_state = :readiness_state, refund_state = 'none', dispute_state = 'clear', "
                "last_transition_reason_code = 'order_backfill', last_transition_note = :last_transition_note WHERE id = :order_id"
            ),
            {
                "customer_refs_json": json.dumps(
                    {
                        "customer_ref": row["customer_ref"],
                        "customer_email": row["customer_email"],
                        "customer_name": row["customer_name"],
                        "customer_phone": row["customer_phone"],
                        "guest_company_name": row["guest_company_name"],
                    }
                ),
                "supplier_refs_json": json.dumps(supplier_refs),
                "internal_owner_user_id": row["owner_user_id"] or row["assignee_user_id"],
                "payment_state": "created",
                "logistics_state": "planning",
                "readiness_state": "not_ready",
                "last_transition_note": row["acceptance_reason"],
                "order_id": row["id"],
            },
        )
        line_id = str(uuid4())
        payment_id = str(uuid4())
        bind.execute(
            sa.text(
                "INSERT INTO order_lines "
                "(id, code, order_id, catalog_item_id, line_type, title, quantity, unit_label, line_amount, currency_code, line_status, "
                "planned_supplier_ref, planned_stage_refs_json, readiness_state, delivery_state, refund_state, dispute_state, "
                "last_transition_reason_code, last_transition_note, archived_at, archived_reason, deleted_at, deleted_reason, created_at, updated_at) "
                "VALUES "
                "(:id, :code, :order_id, :catalog_item_id, :line_type, :title, 1, 'lot', :line_amount, :currency_code, 'created', "
                ":planned_supplier_ref, :planned_stage_refs_json, 'not_ready', 'pending', 'none', 'clear', "
                "'order_backfill', :last_transition_note, NULL, NULL, NULL, NULL, :created_at, :updated_at)"
            ),
            {
                "id": line_id,
                "code": f"ORL-{index:05d}",
                "order_id": row["id"],
                "catalog_item_id": row["catalog_item_id"],
                "line_type": "catalog_service" if row["catalog_item_id"] else "service_context",
                "title": row["title"] or row["item_service_context"] or row["code"],
                "line_amount": row["amount"],
                "currency_code": row["currency_code"] or "VND",
                "planned_supplier_ref": row["supplier_ref"],
                "planned_stage_refs_json": json.dumps(["commercial_confirmed", "production_pending"]),
                "last_transition_note": row["acceptance_reason"],
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or now,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO payment_records "
                "(id, code, order_id, payment_state, amount, currency_code, payment_ref, provider_ref, note, created_by_user_id, "
                "confirmed_at, failed_at, refunded_at, last_transition_reason_code, archived_at, archived_reason, deleted_at, deleted_reason, created_at, updated_at) "
                "VALUES "
                "(:id, :code, :order_id, 'created', :amount, :currency_code, NULL, NULL, :note, :created_by_user_id, "
                "NULL, NULL, NULL, 'order_backfill', NULL, NULL, NULL, NULL, :created_at, :updated_at)"
            ),
            {
                "id": payment_id,
                "code": f"PAY-{index:05d}",
                "order_id": row["id"],
                "amount": row["amount"],
                "currency_code": row["currency_code"] or "VND",
                "note": row["acceptance_reason"],
                "created_by_user_id": row["owner_user_id"] or row["assignee_user_id"],
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or now,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO internal_ledger_entries "
                "(id, code, order_id, payment_record_id, entry_kind, direction, entry_state, amount, currency_code, reason_code, note, created_by_user_id, created_at, updated_at) "
                "VALUES "
                "(:id, :code, :order_id, :payment_record_id, 'payment_expected', 'debit', 'open', :amount, :currency_code, 'order_backfill', :note, :created_by_user_id, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid4()),
                "code": f"LED-{index:05d}",
                "order_id": row["id"],
                "payment_record_id": payment_id,
                "amount": row["amount"],
                "currency_code": row["currency_code"] or "VND",
                "note": row["acceptance_reason"],
                "created_by_user_id": row["owner_user_id"] or row["assignee_user_id"],
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or now,
            },
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    op.drop_table("internal_ledger_entries")
    op.drop_table("payment_records")
    op.drop_table("order_lines")
    if dialect != "sqlite":
        op.drop_constraint("fk_orders_internal_owner", "orders", type_="foreignkey")
    op.drop_column("orders", "last_transition_note")
    op.drop_column("orders", "last_transition_reason_code")
    op.drop_column("orders", "dispute_state")
    op.drop_column("orders", "refund_state")
    op.drop_column("orders", "readiness_state")
    op.drop_column("orders", "logistics_state")
    op.drop_column("orders", "payment_state")
    op.drop_column("orders", "internal_owner_user_id")
    op.drop_column("orders", "supplier_refs_json")
    op.drop_column("orders", "customer_refs_json")
