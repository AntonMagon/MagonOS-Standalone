"""wave1 status language alignment

Revision ID: 20260417_0010
Revises: 20260417_0009
Create Date: 2026-04-17 22:10:00
"""

from __future__ import annotations

from alembic import op


revision = "20260417_0010"
down_revision = "20260417_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    # RU: Postgres хранит final_flag как boolean и не принимает sqlite-style `= 1`, поэтому литерал берём по dialect.
    final_flag_true = "1" if dialect == "sqlite" else "TRUE"
    # RU: Эта миграция не расширяет модель, а выравнивает живые статусы по обновлённой wave1-терминологии из gpt_doc.
    bind.exec_driver_sql("UPDATE suppliers SET supplier_status = 'discovered' WHERE supplier_status = 'candidate'")
    bind.exec_driver_sql("UPDATE suppliers SET supplier_status = 'trusted' WHERE supplier_status = 'approved'")

    bind.exec_driver_sql(
        """
        UPDATE supplier_companies
        SET supplier_status = CASE
            WHEN trust_level = 'trusted' THEN 'trusted'
            WHEN trust_level = 'capability_confirmed' THEN 'capability_confirmed'
            WHEN trust_level = 'contact_confirmed' THEN 'contact_confirmed'
            WHEN trust_level = 'normalized' THEN 'normalized'
            ELSE 'discovered'
        END
        WHERE supplier_status IN ('candidate', 'reviewing')
        """
    )

    bind.exec_driver_sql("UPDATE offers SET offer_status = 'draft' WHERE offer_status = 'prepared'")
    bind.exec_driver_sql(
        "UPDATE offers SET offer_status = 'awaiting_confirmation' WHERE offer_status = 'sent' AND confirmation_state = 'pending'"
    )
    bind.exec_driver_sql("UPDATE offer_versions SET version_status = 'draft' WHERE version_status = 'prepared'")

    bind.exec_driver_sql("UPDATE orders SET order_status = 'awaiting_payment' WHERE order_status = 'created'")
    bind.exec_driver_sql("UPDATE orders SET order_status = 'paid' WHERE order_status = 'awaiting_payment' AND payment_state = 'confirmed'")
    bind.exec_driver_sql("UPDATE orders SET order_status = 'in_production' WHERE order_status = 'confirmed_start'")
    bind.exec_driver_sql("UPDATE orders SET order_status = 'in_delivery' WHERE order_status = 'partially_delivered'")

    bind.exec_driver_sql(
        f"""
        UPDATE files_media
        SET check_state = CASE
            WHEN final_flag = {final_flag_true} AND check_state IN ('approved', 'passed') THEN 'approved_final'
            WHEN check_state IN ('pending_review') THEN 'needs_manual_review'
            WHEN check_state IN ('approved') THEN 'passed'
            WHEN check_state IN ('rejected', 'blocked') THEN 'failed'
            ELSE check_state
        END
        """
    )
    bind.exec_driver_sql(
        f"""
        UPDATE file_versions
        SET check_state = CASE
            WHEN final_flag = {final_flag_true} AND check_state IN ('approved', 'passed') THEN 'approved_final'
            WHEN check_state IN ('pending_review') THEN 'needs_manual_review'
            WHEN check_state IN ('approved') THEN 'passed'
            WHEN check_state IN ('rejected', 'blocked') THEN 'failed'
            ELSE check_state
        END
        """
    )
    bind.exec_driver_sql(
        """
        UPDATE file_checks
        SET check_state = CASE
            WHEN check_state = 'pending_review' THEN 'needs_manual_review'
            WHEN check_state = 'approved' THEN 'passed'
            WHEN check_state IN ('rejected', 'blocked') THEN 'failed'
            ELSE check_state
        END
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("UPDATE suppliers SET supplier_status = 'candidate' WHERE supplier_status = 'discovered'")
    bind.exec_driver_sql("UPDATE suppliers SET supplier_status = 'approved' WHERE supplier_status = 'trusted'")
    bind.exec_driver_sql(
        """
        UPDATE supplier_companies
        SET supplier_status = CASE
            WHEN trust_level = 'discovered' THEN 'reviewing'
            WHEN trust_level = 'normalized' THEN 'reviewing'
            ELSE 'candidate'
        END
        WHERE supplier_status IN ('discovered', 'normalized', 'contact_confirmed', 'capability_confirmed', 'trusted')
        """
    )

    bind.exec_driver_sql("UPDATE offers SET offer_status = 'prepared' WHERE offer_status = 'draft'")
    bind.exec_driver_sql("UPDATE offers SET offer_status = 'sent' WHERE offer_status = 'awaiting_confirmation'")
    bind.exec_driver_sql("UPDATE offer_versions SET version_status = 'prepared' WHERE version_status = 'draft'")

    bind.exec_driver_sql("UPDATE orders SET order_status = 'created' WHERE order_status = 'awaiting_payment'")
    bind.exec_driver_sql("UPDATE orders SET order_status = 'created' WHERE order_status = 'paid'")
    bind.exec_driver_sql("UPDATE orders SET order_status = 'confirmed_start' WHERE order_status = 'in_production'")
    bind.exec_driver_sql("UPDATE orders SET order_status = 'partially_delivered' WHERE order_status = 'in_delivery' AND logistics_state = 'partial_delivery'")

    bind.exec_driver_sql(
        """
        UPDATE files_media
        SET check_state = CASE
            WHEN check_state = 'needs_manual_review' THEN 'pending_review'
            WHEN check_state = 'passed' THEN 'approved'
            WHEN check_state = 'failed' THEN 'rejected'
            WHEN check_state = 'approved_final' THEN 'approved'
            ELSE check_state
        END
        """
    )
    bind.exec_driver_sql(
        """
        UPDATE file_versions
        SET check_state = CASE
            WHEN check_state = 'needs_manual_review' THEN 'pending_review'
            WHEN check_state = 'passed' THEN 'approved'
            WHEN check_state = 'failed' THEN 'rejected'
            WHEN check_state = 'approved_final' THEN 'approved'
            ELSE check_state
        END
        """
    )
    bind.exec_driver_sql(
        """
        UPDATE file_checks
        SET check_state = CASE
            WHEN check_state = 'needs_manual_review' THEN 'pending_review'
            WHEN check_state = 'passed' THEN 'approved'
            WHEN check_state = 'failed' THEN 'rejected'
            ELSE check_state
        END
        """
    )
