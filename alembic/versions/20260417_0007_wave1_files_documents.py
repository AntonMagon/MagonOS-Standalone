"""wave1 files and documents contour

Revision ID: 20260417_0007
Revises: 20260417_0006
Create Date: 2026-04-17 23:10:00
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260417_0007"
down_revision = "20260417_0006"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _guess_extension(filename: str | None) -> str | None:
    if not filename:
        return None
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix or None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    now = _utc_now()

    op.add_column("files_media", sa.Column("file_type", sa.String(length=32), nullable=False, server_default="attachment"))
    op.add_column("files_media", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("files_media", sa.Column("storage_backend", sa.String(length=32), nullable=False, server_default="local"))
    op.add_column("files_media", sa.Column("file_extension", sa.String(length=16), nullable=True))
    op.add_column("files_media", sa.Column("byte_size", sa.Integer(), nullable=True))
    op.add_column("files_media", sa.Column("current_version_no", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("files_media", sa.Column("check_state", sa.String(length=32), nullable=False, server_default="pending_review"))
    op.add_column("files_media", sa.Column("visibility_scope", sa.String(length=32), nullable=False, server_default="internal"))
    op.add_column("files_media", sa.Column("final_flag", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("files_media", sa.Column("latest_version_id", sa.String(length=36), nullable=True))

    op.add_column("documents", sa.Column("template_key", sa.String(length=64), nullable=False, server_default="internal_job"))
    op.add_column("documents", sa.Column("visibility_scope", sa.String(length=32), nullable=False, server_default="internal"))
    op.add_column("documents", sa.Column("current_version_no", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("published_version_no", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("sent_state", sa.String(length=32), nullable=False, server_default="draft"))
    op.add_column("documents", sa.Column("confirmation_state", sa.String(length=32), nullable=False, server_default="pending"))

    op.create_table(
        "file_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("file_asset_id", sa.String(length=36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("version_status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_extension", sa.String(length=16), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False, server_default="attachment"),
        sa.Column("check_state", sa.String(length=32), nullable=False, server_default="pending_review"),
        sa.Column("visibility_scope", sa.String(length=32), nullable=False, server_default="internal"),
        sa.Column("final_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["file_asset_id"], ["files_media.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("file_asset_id", "version_no", name="uq_file_versions_asset_version"),
    )

    op.create_table(
        "file_checks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("file_asset_id", sa.String(length=36), nullable=False),
        sa.Column("file_version_id", sa.String(length=36), nullable=False),
        sa.Column("check_kind", sa.String(length=32), nullable=False),
        sa.Column("check_state", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("checked_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["checked_by_user_id"], ["users_access_users.id"]),
        sa.ForeignKeyConstraint(["file_asset_id"], ["files_media.id"]),
        sa.ForeignKeyConstraint(["file_version_id"], ["file_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("version_status", sa.String(length=32), nullable=False, server_default="published"),
        sa.Column("file_asset_id", sa.String(length=36), nullable=False),
        sa.Column("file_version_id", sa.String(length=36), nullable=False),
        sa.Column("sent_state", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("confirmation_state", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("visibility_scope", sa.String(length=32), nullable=False, server_default="internal"),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("generated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_reason", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["file_asset_id"], ["files_media.id"]),
        sa.ForeignKeyConstraint(["file_version_id"], ["file_versions.id"]),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users_access_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("document_id", "version_no", name="uq_document_versions_document_version"),
    )

    if dialect != "sqlite":
        op.create_foreign_key("fk_files_media_latest_version", "files_media", "file_versions", ["latest_version_id"], ["id"])

    files = list(
        bind.execute(
            sa.text(
                "SELECT id, code, owner_type, owner_id, original_name, storage_key, mime_type, visibility, uploaded_by_user_id, "
                "created_at, updated_at FROM files_media"
            )
        ).mappings()
    )

    file_version_map: dict[str, str] = {}
    for index, row in enumerate(files, start=1):
        extension = _guess_extension(row["original_name"])
        version_id = str(uuid4())
        file_version_map[row["id"]] = version_id
        bind.execute(
            sa.text(
                "UPDATE files_media SET file_type = :file_type, title = COALESCE(title, original_name), storage_backend = 'local', "
                "file_extension = :file_extension, byte_size = COALESCE(byte_size, 0), current_version_no = 1, check_state = 'approved', "
                "visibility_scope = COALESCE(visibility, 'internal'), final_flag = 1, latest_version_id = :latest_version_id WHERE id = :file_id"
            ),
            {
                "file_type": "attachment",
                "file_extension": extension,
                "latest_version_id": version_id,
                "file_id": row["id"],
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO file_versions "
                "(id, code, file_asset_id, version_no, version_status, original_name, storage_key, storage_backend, mime_type, "
                "file_extension, byte_size, checksum_sha256, file_type, check_state, visibility_scope, final_flag, created_by_user_id, "
                "archived_at, archived_reason, deleted_at, deleted_reason, created_at, updated_at) "
                "VALUES "
                "(:id, :code, :file_asset_id, 1, 'active', :original_name, :storage_key, 'local', :mime_type, "
                ":file_extension, :byte_size, :checksum_sha256, 'attachment', 'approved', :visibility_scope, 1, :created_by_user_id, "
                "NULL, NULL, NULL, NULL, :created_at, :updated_at)"
            ),
            {
                "id": version_id,
                "code": f"FVR-{index:05d}",
                "file_asset_id": row["id"],
                "original_name": row["original_name"],
                "storage_key": row["storage_key"],
                "mime_type": row["mime_type"] or "application/octet-stream",
                "file_extension": extension,
                "byte_size": 0,
                "checksum_sha256": "0" * 64,
                "visibility_scope": row["visibility"] or "internal",
                "created_by_user_id": row["uploaded_by_user_id"],
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or now,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO file_checks "
                "(id, code, file_asset_id, file_version_id, check_kind, check_state, reason_code, message, details_json, checked_by_user_id, created_at, updated_at) "
                "VALUES "
                "(:id, :code, :file_asset_id, :file_version_id, 'legacy_backfill', 'approved', 'legacy_file_backfill', :message, NULL, :checked_by_user_id, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid4()),
                "code": f"FCK-{index:05d}",
                "file_asset_id": row["id"],
                "file_version_id": version_id,
                "message": "Legacy file asset backfilled into managed contour.",
                "checked_by_user_id": row["uploaded_by_user_id"],
                "created_at": row["updated_at"] or row["created_at"] or now,
                "updated_at": row["updated_at"] or row["created_at"] or now,
            },
        )

    documents = list(
        bind.execute(
            sa.text(
                "SELECT id, code, owner_type, owner_id, file_id, document_type, title, visibility, created_by_user_id, created_at, updated_at FROM documents"
            )
        ).mappings()
    )
    for index, row in enumerate(documents, start=1):
        version_id = file_version_map.get(row["file_id"]) if row["file_id"] else None
        bind.execute(
            sa.text(
                "UPDATE documents SET template_key = :template_key, visibility_scope = COALESCE(visibility, 'internal'), "
                "current_version_no = :current_version_no, published_version_no = :published_version_no, sent_state = 'draft', confirmation_state = 'pending' "
                "WHERE id = :document_id"
            ),
            {
                "template_key": row["document_type"] or "internal_job",
                "current_version_no": 1 if version_id else 0,
                "published_version_no": 1 if version_id else None,
                "document_id": row["id"],
            },
        )
        if version_id:
            bind.execute(
                sa.text(
                    "INSERT INTO document_versions "
                    "(id, code, document_id, version_no, version_status, file_asset_id, file_version_id, sent_state, confirmation_state, "
                    "published_at, sent_at, confirmed_at, replaced_at, reason_code, note, visibility_scope, payload_json, generated_by_user_id, "
                    "archived_at, archived_reason, deleted_at, deleted_reason, created_at, updated_at) "
                    "VALUES "
                    "(:id, :code, :document_id, 1, 'published', :file_asset_id, :file_version_id, 'draft', 'pending', "
                    ":published_at, NULL, NULL, NULL, 'legacy_document_backfill', :note, :visibility_scope, NULL, :generated_by_user_id, "
                    "NULL, NULL, NULL, NULL, :created_at, :updated_at)"
                ),
                {
                    "id": str(uuid4()),
                    "code": f"DVN-{index:05d}",
                    "document_id": row["id"],
                    "file_asset_id": row["file_id"],
                    "file_version_id": version_id,
                    "published_at": row["updated_at"] or row["created_at"] or now,
                    "note": "Legacy document backfilled into managed contour.",
                    "visibility_scope": row["visibility"] or "internal",
                    "generated_by_user_id": row["created_by_user_id"],
                    "created_at": row["created_at"] or now,
                    "updated_at": row["updated_at"] or now,
                },
            )

    if dialect != "sqlite":
        op.alter_column("files_media", "file_type", server_default=None)
        op.alter_column("files_media", "storage_backend", server_default=None)
        op.alter_column("files_media", "current_version_no", server_default=None)
        op.alter_column("files_media", "check_state", server_default=None)
        op.alter_column("files_media", "visibility_scope", server_default=None)
        op.alter_column("files_media", "final_flag", server_default=None)
        op.alter_column("documents", "template_key", server_default=None)
        op.alter_column("documents", "visibility_scope", server_default=None)
        op.alter_column("documents", "current_version_no", server_default=None)
        op.alter_column("documents", "sent_state", server_default=None)
        op.alter_column("documents", "confirmation_state", server_default=None)


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect != "sqlite":
        op.drop_constraint("fk_files_media_latest_version", "files_media", type_="foreignkey")

    op.drop_table("document_versions")
    op.drop_table("file_checks")
    op.drop_table("file_versions")

    op.drop_column("documents", "confirmation_state")
    op.drop_column("documents", "sent_state")
    op.drop_column("documents", "published_version_no")
    op.drop_column("documents", "current_version_no")
    op.drop_column("documents", "visibility_scope")
    op.drop_column("documents", "template_key")

    op.drop_column("files_media", "latest_version_id")
    op.drop_column("files_media", "final_flag")
    op.drop_column("files_media", "visibility_scope")
    op.drop_column("files_media", "check_state")
    op.drop_column("files_media", "current_version_no")
    op.drop_column("files_media", "byte_size")
    op.drop_column("files_media", "file_extension")
    op.drop_column("files_media", "storage_backend")
    op.drop_column("files_media", "title")
    op.drop_column("files_media", "file_type")
