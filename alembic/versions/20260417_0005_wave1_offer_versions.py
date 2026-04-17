"""wave1 offer versions

Revision ID: 20260417_0005
Revises: 20260417_0004
Create Date: 2026-04-17 20:10:00
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260417_0005"
down_revision = "20260417_0004"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.add_column("offers", sa.Column("request_ref", sa.String(length=32), nullable=True))
    op.add_column("offers", sa.Column("current_version_no", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("offers", sa.Column("confirmation_state", sa.String(length=32), nullable=False, server_default="pending"))
    op.add_column("offers", sa.Column("lead_time_days", sa.Integer(), nullable=True))
    op.add_column("offers", sa.Column("terms_text", sa.Text(), nullable=True))
    op.add_column("offers", sa.Column("scenario_type", sa.String(length=32), nullable=False, server_default="standard"))
    op.add_column("offers", sa.Column("supplier_ref", sa.String(length=64), nullable=True))

    op.create_table(
        "offer_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("version_status", sa.String(length=32), nullable=False, server_default="prepared"),
        sa.Column("confirmation_state", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default="VND"),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("terms_text", sa.Text(), nullable=True),
        sa.Column("scenario_type", sa.String(length=32), nullable=False, server_default="standard"),
        sa.Column("supplier_ref", sa.String(length=64), nullable=True),
        sa.Column("public_summary", sa.Text(), nullable=True),
        sa.Column("change_reason_code", sa.String(length=128), nullable=False),
        sa.Column("change_note", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("offer_id", "version_no", name="uq_offer_versions_offer_version_no"),
    )

    op.create_table(
        "offer_confirmation_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("offer_version_id", sa.String(length=36), nullable=False),
        sa.Column("confirmation_action", sa.String(length=32), nullable=False),
        sa.Column("confirmation_state", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.ForeignKeyConstraint(["offer_version_id"], ["offer_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "offer_comparison_metadata",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("offer_version_id", sa.String(length=36), nullable=False),
        sa.Column("comparison_title", sa.String(length=255), nullable=True),
        sa.Column("comparison_rank", sa.Integer(), nullable=True),
        sa.Column("recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("highlights_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.ForeignKeyConstraint(["offer_version_id"], ["offer_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "offer_critical_change_reset_reasons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("previous_offer_version_id", sa.String(length=36), nullable=False),
        sa.Column("new_offer_version_id", sa.String(length=36), nullable=False),
        sa.Column("previous_confirmation_state", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["new_offer_version_id"], ["offer_versions.id"]),
        sa.ForeignKeyConstraint(["offer_id"], ["offers.id"]),
        sa.ForeignKeyConstraint(["previous_offer_version_id"], ["offer_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.add_column("orders", sa.Column("offer_version_id", sa.String(length=36), nullable=True))
    if dialect != "sqlite":
        op.create_foreign_key("fk_orders_offer_version", "orders", "offer_versions", ["offer_version_id"], ["id"])

    offers = list(
        bind.execute(
            sa.text(
                "SELECT offers.id, offers.code, offers.request_id, requests.code AS request_code, "
                "offers.offer_status, offers.amount, offers.currency_code, offers.public_summary, offers.transition_reason, "
                "offers.created_at, offers.updated_at "
                "FROM offers JOIN requests ON requests.id = offers.request_id"
            )
        ).mappings()
    )
    offer_version_map: dict[str, str] = {}
    now = _utc_now()
    for index, row in enumerate(offers, start=1):
        bind.execute(
            sa.text(
                "UPDATE offers SET request_ref = :request_ref, current_version_no = 1, "
                "confirmation_state = :confirmation_state, scenario_type = 'standard' "
                "WHERE id = :offer_id"
            ),
            {
                "request_ref": row["request_code"],
                "confirmation_state": "accepted" if row["offer_status"] == "accepted" else "pending",
                "offer_id": row["id"],
            },
        )
        version_id = str(uuid4())
        offer_version_map[row["id"]] = version_id
        bind.execute(
            sa.text(
                "INSERT INTO offer_versions "
                "(id, code, offer_id, version_no, version_status, confirmation_state, amount, currency_code, "
                "lead_time_days, terms_text, scenario_type, supplier_ref, public_summary, change_reason_code, change_note, "
                "is_current, archived_at, archived_reason, deleted_at, deleted_reason, created_at, updated_at) "
                "VALUES "
                "(:id, :code, :offer_id, 1, :version_status, :confirmation_state, :amount, :currency_code, "
                ":lead_time_days, :terms_text, 'standard', :supplier_ref, :public_summary, :change_reason_code, :change_note, "
                ":is_current, NULL, NULL, NULL, NULL, :created_at, :updated_at)"
            ),
            {
                "id": version_id,
                "code": f"OFV-{index:05d}",
                "offer_id": row["id"],
                "version_status": row["offer_status"] if row["offer_status"] != "accepted" else "sent",
                "confirmation_state": "accepted" if row["offer_status"] == "accepted" else "pending",
                "amount": row["amount"],
                "currency_code": row["currency_code"] or "VND",
                "lead_time_days": None,
                "terms_text": None,
                "supplier_ref": None,
                "public_summary": row["public_summary"],
                "change_reason_code": "offer_version_backfill",
                "change_note": row["transition_reason"],
                "is_current": True,
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or now,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO offer_comparison_metadata "
                "(id, code, offer_id, offer_version_id, comparison_title, comparison_rank, recommended, highlights_json, metadata_json, created_at, updated_at) "
                "VALUES (:id, :code, :offer_id, :offer_version_id, :comparison_title, :comparison_rank, :recommended, :highlights_json, :metadata_json, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid4()),
                "code": f"OCM-{index:05d}",
                "offer_id": row["id"],
                "offer_version_id": version_id,
                "comparison_title": row["public_summary"] or row["request_code"],
                "comparison_rank": index,
                "recommended": False,
                "highlights_json": None,
                "metadata_json": None,
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or now,
            },
        )
        if row["offer_status"] == "accepted":
            bind.execute(
                sa.text(
                    "INSERT INTO offer_confirmation_records "
                    "(id, code, offer_id, offer_version_id, confirmation_action, confirmation_state, reason_code, note, actor_user_id, actor_role, occurred_at, created_at, updated_at) "
                    "VALUES (:id, :code, :offer_id, :offer_version_id, 'accepted', 'accepted', 'offer_accept_backfill', :note, NULL, 'system', :occurred_at, :created_at, :updated_at)"
                ),
                {
                    "id": str(uuid4()),
                    "code": f"OCF-{index:05d}",
                    "offer_id": row["id"],
                    "offer_version_id": version_id,
                    "note": row["transition_reason"],
                    "occurred_at": row["updated_at"] or now,
                    "created_at": row["updated_at"] or now,
                    "updated_at": row["updated_at"] or now,
                },
            )

    orders = list(bind.execute(sa.text("SELECT id, offer_id FROM orders")).mappings())
    for row in orders:
        version_id = offer_version_map.get(row["offer_id"])
        if version_id:
            bind.execute(
                sa.text("UPDATE orders SET offer_version_id = :offer_version_id WHERE id = :order_id"),
                {"offer_version_id": version_id, "order_id": row["id"]},
            )

    if dialect != "sqlite":
        op.alter_column("offers", "request_ref", nullable=False)
        op.alter_column("orders", "offer_version_id", nullable=False)
        op.alter_column("offers", "current_version_no", server_default=None)
        op.alter_column("offers", "confirmation_state", server_default=None)
        op.alter_column("offers", "scenario_type", server_default=None)
    else:
        bind.execute(sa.text("UPDATE offers SET request_ref = code WHERE request_ref IS NULL"))


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "sqlite":
        op.drop_constraint("fk_orders_offer_version", "orders", type_="foreignkey")
    op.drop_column("orders", "offer_version_id")

    op.drop_table("offer_critical_change_reset_reasons")
    op.drop_table("offer_comparison_metadata")
    op.drop_table("offer_confirmation_records")
    op.drop_table("offer_versions")

    op.drop_column("offers", "supplier_ref")
    op.drop_column("offers", "scenario_type")
    op.drop_column("offers", "terms_text")
    op.drop_column("offers", "lead_time_days")
    op.drop_column("offers", "confirmation_state")
    op.drop_column("offers", "current_version_no")
    op.drop_column("offers", "request_ref")
