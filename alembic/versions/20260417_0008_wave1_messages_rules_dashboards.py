"""wave1 messages, rules, notifications, dashboards

Revision ID: 20260417_0008
Revises: 20260417_0007
Create Date: 2026-04-17 23:55:00
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260417_0008"
down_revision = "20260417_0007"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    bind = op.get_bind()
    now = _utc_now()

    op.add_column("rules_engine_rules", sa.Column("rule_kind", sa.String(length=32), nullable=False, server_default="transition_guard"))
    op.add_column("rules_engine_rules", sa.Column("latest_version_no", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("rules_engine_rules", sa.Column("metadata_json", sa.JSON(), nullable=True))

    op.create_table(
        "reason_codes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="info"),
        sa.Column("default_visibility_scope", sa.String(length=32), nullable=False, server_default="internal"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "rules_engine_rule_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("rule_definition_id", sa.String(length=36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("version_status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("explainability_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["rule_definition_id"], ["rules_engine_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("rule_definition_id", "version_no", name="uq_rule_version_per_rule"),
    )

    op.create_table(
        "notification_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("rule_definition_id", sa.String(length=36), nullable=True),
        sa.Column("rule_version_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("recipient_scope", sa.String(length=32), nullable=False, server_default="internal"),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="inbox"),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("min_interval_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["rule_definition_id"], ["rules_engine_rules.id"]),
        sa.ForeignKeyConstraint(["rule_version_id"], ["rules_engine_rule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "escalation_hints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.String(length=64), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="info"),
        sa.Column("sla_minutes", sa.Integer(), nullable=True),
        sa.Column("overdue_after_minutes", sa.Integer(), nullable=True),
        sa.Column("dashboard_bucket", sa.String(length=64), nullable=False, server_default="attention"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "message_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("owner_type", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("entry_kind", sa.String(length=32), nullable=False, server_default="event"),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="system"),
        sa.Column("actor_type", sa.String(length=32), nullable=False, server_default="system"),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message_type", sa.String(length=64), nullable=True),
        sa.Column("visibility_scope", sa.String(length=32), nullable=False, server_default="internal"),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_audit_event_id", sa.String(length=36), nullable=True),
        sa.Column("parent_message_id", sa.String(length=36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["parent_message_id"], ["message_events.id"]),
        sa.ForeignKeyConstraint(["source_audit_event_id"], ["audit_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_message_events_owner_timeline", "message_events", ["owner_type", "owner_id", "occurred_at"])
    op.create_index("ix_message_events_visibility", "message_events", ["visibility_scope", "occurred_at"])

    rules = list(bind.execute(sa.text("SELECT id, code, config_json, created_at, updated_at FROM rules_engine_rules")).mappings())
    for index, row in enumerate(rules, start=1):
        bind.execute(
            sa.text("UPDATE rules_engine_rules SET rule_kind = COALESCE(rule_kind, 'transition_guard'), latest_version_no = 1 WHERE id = :rule_id"),
            {"rule_id": row["id"]},
        )
        bind.execute(
            sa.text(
                "INSERT INTO rules_engine_rule_versions "
                "(id, code, rule_definition_id, version_no, version_status, checksum, explainability_json, metadata_json, effective_from, effective_to, created_by_user_id, archived_at, archived_reason, deleted_at, deleted_reason, created_at, updated_at) "
                "VALUES "
                "(:id, :code, :rule_definition_id, 1, 'active', :checksum, NULL, :metadata_json, :effective_from, NULL, NULL, NULL, NULL, NULL, NULL, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid4()),
                "code": f"RLV-{index:05d}",
                "rule_definition_id": row["id"],
                "checksum": str(row["config_json"]) if row["config_json"] is not None else None,
                "metadata_json": None,
                "effective_from": row["created_at"] or now,
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or now,
            },
        )

    audit_rows = list(
        bind.execute(
            sa.text(
                "SELECT id, code, module_name, action, entity_type, entity_id, entity_code, actor_user_id, actor_role, reason, visibility, request_id, payload_json, created_at, updated_at "
                "FROM audit_events ORDER BY created_at ASC, updated_at ASC"
            )
        ).mappings()
    )
    for index, row in enumerate(audit_rows, start=1):
        owner_type = {"supplier_company": "supplier", "file_asset": "file"}.get(row["entity_type"], row["entity_type"])
        visibility_scope = "customer" if row["visibility"] == "customer" else "internal"
        # RU: Postgres/psycopg не адаптирует Python dict в raw SQL text bind автоматически, поэтому JSON явно сериализуем ещё в миграции.
        bind.execute(
            sa.text(
                "INSERT INTO message_events "
                "(id, code, owner_type, owner_id, entry_kind, channel, actor_type, actor_user_id, actor_role, event_type, message_type, visibility_scope, reason_code, title, body, dedupe_key, payload_json, occurred_at, source_audit_event_id, parent_message_id, archived_at, archived_reason, deleted_at, deleted_reason, created_at, updated_at) "
                "VALUES "
                "(:id, :code, :owner_type, :owner_id, 'event', 'system', :actor_type, :actor_user_id, :actor_role, :event_type, 'audit_event', :visibility_scope, :reason_code, :title, :body, NULL, :payload_json, :occurred_at, :source_audit_event_id, NULL, NULL, NULL, NULL, NULL, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid4()),
                "code": f"MSG-{index:05d}",
                "owner_type": owner_type,
                "owner_id": row["entity_id"],
                "actor_type": "user" if row["actor_user_id"] else "system",
                "actor_user_id": row["actor_user_id"],
                "actor_role": row["actor_role"],
                "event_type": row["action"],
                "visibility_scope": visibility_scope,
                "reason_code": row["reason"],
                "title": row["action"],
                "body": row["reason"],
                "payload_json": json.dumps(row["payload_json"]) if row["payload_json"] is not None else None,
                "occurred_at": row["created_at"] or now,
                "source_audit_event_id": row["id"],
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or row["created_at"] or now,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_message_events_visibility", table_name="message_events")
    op.drop_index("ix_message_events_owner_timeline", table_name="message_events")
    op.drop_table("message_events")
    op.drop_table("escalation_hints")
    op.drop_table("notification_rules")
    op.drop_table("rules_engine_rule_versions")
    op.drop_table("reason_codes")
    op.drop_column("rules_engine_rules", "metadata_json")
    op.drop_column("rules_engine_rules", "latest_version_no")
    op.drop_column("rules_engine_rules", "rule_kind")
