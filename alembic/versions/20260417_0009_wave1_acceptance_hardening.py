"""wave1 acceptance hardening

Revision ID: 20260417_0009
Revises: 20260417_0008
Create Date: 2026-04-17 20:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260417_0009"
down_revision = "20260417_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("supplier_raw_ingests")}
    # RU: Миграция должна быть переживаемой для локального SQLite, где часть acceptance-колонок уже могла появиться из предыдущего частичного прогона.
    if "failed_at" not in existing_columns:
        op.add_column("supplier_raw_ingests", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
    if "last_retry_at" not in existing_columns:
        op.add_column("supplier_raw_ingests", sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True))
    if "retry_count" not in existing_columns:
        op.add_column("supplier_raw_ingests", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    if "failure_code" not in existing_columns:
        op.add_column("supplier_raw_ingests", sa.Column("failure_code", sa.String(length=128), nullable=True))
    if "failure_detail" not in existing_columns:
        op.add_column("supplier_raw_ingests", sa.Column("failure_detail", sa.Text(), nullable=True))

    if bind.dialect.name != "sqlite" and "retry_count" not in existing_columns:
        op.alter_column("supplier_raw_ingests", "retry_count", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("supplier_raw_ingests")}
    if "failure_detail" in existing_columns:
        op.drop_column("supplier_raw_ingests", "failure_detail")
    if "failure_code" in existing_columns:
        op.drop_column("supplier_raw_ingests", "failure_code")
    if "retry_count" in existing_columns:
        op.drop_column("supplier_raw_ingests", "retry_count")
    if "last_retry_at" in existing_columns:
        op.drop_column("supplier_raw_ingests", "last_retry_at")
    if "failed_at" in existing_columns:
        op.drop_column("supplier_raw_ingests", "failed_at")
