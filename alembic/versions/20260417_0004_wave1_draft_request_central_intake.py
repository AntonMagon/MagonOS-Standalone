"""wave1 draft request central intake

Revision ID: 20260417_0004
Revises: 20260417_0003
Create Date: 2026-04-17 18:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260417_0004"
down_revision = "20260417_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    op.add_column("draft_requests", sa.Column("submitted_request_id", sa.String(length=36), nullable=True))
    op.add_column("draft_requests", sa.Column("item_service_context", sa.Text(), nullable=True))
    op.add_column("draft_requests", sa.Column("city", sa.String(length=128), nullable=True))
    op.add_column("draft_requests", sa.Column("geo_json", sa.JSON(), nullable=True))
    op.add_column("draft_requests", sa.Column("source_channel", sa.String(length=32), nullable=False, server_default="web_public"))
    op.add_column("draft_requests", sa.Column("draft_status", sa.String(length=32), nullable=False, server_default="draft"))
    op.add_column("draft_requests", sa.Column("requested_deadline_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("draft_requests", sa.Column("owner_user_id", sa.String(length=36), nullable=True))
    op.add_column("draft_requests", sa.Column("assignee_user_id", sa.String(length=36), nullable=True))
    op.add_column("draft_requests", sa.Column("last_autosaved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("draft_requests", sa.Column("last_customer_activity_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("draft_requests", sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("draft_requests", sa.Column("last_transition_reason_code", sa.String(length=128), nullable=True))
    op.add_column("draft_requests", sa.Column("last_transition_note", sa.Text(), nullable=True))

    op.add_column("requests", sa.Column("customer_ref", sa.String(length=32), nullable=True))
    op.create_index("ix_requests_customer_ref", "requests", ["customer_ref"], unique=True)
    op.add_column("requests", sa.Column("item_service_context", sa.Text(), nullable=True))
    op.add_column("requests", sa.Column("source_channel", sa.String(length=32), nullable=False, server_default="web_public"))
    op.add_column("requests", sa.Column("city", sa.String(length=128), nullable=True))
    op.add_column("requests", sa.Column("geo_json", sa.JSON(), nullable=True))
    op.add_column("requests", sa.Column("requested_deadline_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("requests", sa.Column("owner_user_id", sa.String(length=36), nullable=True))
    op.add_column("requests", sa.Column("assignee_user_id", sa.String(length=36), nullable=True))
    op.add_column("requests", sa.Column("last_transition_reason_code", sa.String(length=128), nullable=True))
    op.add_column("requests", sa.Column("last_transition_note", sa.Text(), nullable=True))

    op.create_table(
        "required_fields_state",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("field_status", sa.String(length=32), nullable=False, server_default="missing"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("current_value", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("owner_type", "owner_id", "field_name", name="uq_required_field_state_owner_field"),
    )

    op.create_table(
        "intake_file_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_kind", sa.String(length=32), nullable=False, server_default="external_link"),
        sa.Column("visibility", sa.String(length=32), nullable=False, server_default="role"),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users_access_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "request_reasons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("reason_kind", sa.String(length=32), nullable=False, server_default="reason"),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users_access_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "request_clarification_cycles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("cycle_index", sa.Integer(), nullable=False),
        sa.Column("cycle_status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("opened_reason_code", sa.String(length=128), nullable=False),
        sa.Column("opened_note", sa.Text(), nullable=True),
        sa.Column("opened_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("closed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["closed_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["opened_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "request_follow_up_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("clarification_cycle_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("follow_up_status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("closed_reason_code", sa.String(length=128), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["clarification_cycle_id"], ["request_clarification_cycles.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    if dialect != "sqlite":
        op.create_foreign_key("fk_draft_requests_submitted_request", "draft_requests", "requests", ["submitted_request_id"], ["id"])
        op.create_foreign_key("fk_draft_requests_owner", "draft_requests", "users_access_users", ["owner_user_id"], ["id"])
        op.create_foreign_key("fk_draft_requests_assignee", "draft_requests", "users_access_users", ["assignee_user_id"], ["id"])
        op.create_foreign_key("fk_requests_owner", "requests", "users_access_users", ["owner_user_id"], ["id"])
        op.create_foreign_key("fk_requests_assignee", "requests", "users_access_users", ["assignee_user_id"], ["id"])
        op.alter_column("draft_requests", "source_channel", server_default=None)
        op.alter_column("draft_requests", "draft_status", server_default=None)
        op.alter_column("requests", "source_channel", server_default=None)

    op.execute(
        sa.text(
            """
            UPDATE draft_requests
            SET source_channel = COALESCE(source_channel, intake_channel, 'web_public'),
                draft_status = CASE
                    WHEN submitted_at IS NOT NULL THEN 'archived'
                    WHEN COALESCE(title, '') = '' AND COALESCE(summary, '') = '' AND COALESCE(customer_email, '') = '' THEN 'draft'
                    WHEN COALESCE(title, '') = '' OR COALESCE(summary, '') = '' OR COALESCE(customer_email, '') = '' THEN 'awaiting_data'
                    ELSE 'ready_to_submit'
                END,
                requested_deadline_at = COALESCE(requested_deadline_at, requested_due_at),
                last_autosaved_at = COALESCE(last_autosaved_at, updated_at, created_at),
                last_customer_activity_at = COALESCE(last_customer_activity_at, updated_at, created_at),
                last_transition_reason_code = COALESCE(last_transition_reason_code, 'legacy_draft_seed')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE requests
            SET source_channel = COALESCE(source_channel, 'web_public'),
                requested_deadline_at = COALESCE(requested_deadline_at, requested_due_at),
                request_status = CASE
                    WHEN request_status IN ('received', 'qualified') THEN 'needs_review'
                    WHEN request_status = 'priced' THEN 'offer_prep'
                    ELSE COALESCE(request_status, 'new')
                END,
                last_transition_reason_code = COALESCE(last_transition_reason_code, 'legacy_request_seed')
            """
        )
    )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect != "sqlite":
        op.drop_constraint("fk_requests_assignee", "requests", type_="foreignkey")
        op.drop_constraint("fk_requests_owner", "requests", type_="foreignkey")
        op.drop_constraint("fk_draft_requests_assignee", "draft_requests", type_="foreignkey")
        op.drop_constraint("fk_draft_requests_owner", "draft_requests", type_="foreignkey")
        op.drop_constraint("fk_draft_requests_submitted_request", "draft_requests", type_="foreignkey")

    op.drop_table("request_follow_up_items")
    op.drop_table("request_clarification_cycles")
    op.drop_table("request_reasons")
    op.drop_table("intake_file_links")
    op.drop_table("required_fields_state")

    op.drop_column("requests", "last_transition_note")
    op.drop_column("requests", "last_transition_reason_code")
    op.drop_column("requests", "assignee_user_id")
    op.drop_column("requests", "owner_user_id")
    op.drop_column("requests", "requested_deadline_at")
    op.drop_column("requests", "geo_json")
    op.drop_column("requests", "city")
    op.drop_column("requests", "source_channel")
    op.drop_column("requests", "item_service_context")
    op.drop_index("ix_requests_customer_ref", table_name="requests")
    op.drop_column("requests", "customer_ref")

    op.drop_column("draft_requests", "last_transition_note")
    op.drop_column("draft_requests", "last_transition_reason_code")
    op.drop_column("draft_requests", "abandoned_at")
    op.drop_column("draft_requests", "last_customer_activity_at")
    op.drop_column("draft_requests", "last_autosaved_at")
    op.drop_column("draft_requests", "assignee_user_id")
    op.drop_column("draft_requests", "owner_user_id")
    op.drop_column("draft_requests", "requested_deadline_at")
    op.drop_column("draft_requests", "draft_status")
    op.drop_column("draft_requests", "source_channel")
    op.drop_column("draft_requests", "geo_json")
    op.drop_column("draft_requests", "city")
    op.drop_column("draft_requests", "item_service_context")
    op.drop_column("draft_requests", "submitted_request_id")
