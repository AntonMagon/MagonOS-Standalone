# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from magon_standalone.foundation.app import create_app


# RU: Order-тесты доказывают, что forbidden transitions и платёжные статусы проверяются на чистой схеме.
def _apply_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    os.environ["MAGON_FOUNDATION_DATABASE_URL"] = database_url
    command.upgrade(config, "head")


class TestFoundationOrders(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite+pysqlite:///{Path(self.tmpdir.name) / 'foundation.sqlite3'}"
        self.legacy_db_path = str(Path(self.tmpdir.name) / "legacy.sqlite3")
        self._previous = {
            key: os.environ.get(key)
            for key in [
                "MAGON_ENV",
                "MAGON_FOUNDATION_DATABASE_URL",
                "MAGON_FOUNDATION_REDIS_URL",
                "MAGON_FOUNDATION_CELERY_BROKER_URL",
                "MAGON_FOUNDATION_CELERY_RESULT_BACKEND",
                "MAGON_FOUNDATION_LEGACY_ENABLED",
                "MAGON_STANDALONE_DB_PATH",
                "MAGON_FOUNDATION_DEFAULT_ADMIN_EMAIL",
                "MAGON_FOUNDATION_DEFAULT_ADMIN_PASSWORD",
                "MAGON_FOUNDATION_DEFAULT_OPERATOR_EMAIL",
                "MAGON_FOUNDATION_DEFAULT_OPERATOR_PASSWORD",
                "MAGON_FOUNDATION_DEFAULT_CUSTOMER_EMAIL",
                "MAGON_FOUNDATION_DEFAULT_CUSTOMER_PASSWORD",
            ]
        }
        os.environ["MAGON_ENV"] = "test"
        os.environ["MAGON_FOUNDATION_DATABASE_URL"] = self.database_url
        os.environ["MAGON_FOUNDATION_REDIS_URL"] = ""
        os.environ["MAGON_FOUNDATION_CELERY_BROKER_URL"] = "memory://"
        os.environ["MAGON_FOUNDATION_CELERY_RESULT_BACKEND"] = "cache+memory://"
        os.environ["MAGON_FOUNDATION_LEGACY_ENABLED"] = "false"
        os.environ["MAGON_STANDALONE_DB_PATH"] = self.legacy_db_path
        os.environ["MAGON_FOUNDATION_DEFAULT_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["MAGON_FOUNDATION_DEFAULT_ADMIN_PASSWORD"] = "admin123"
        os.environ["MAGON_FOUNDATION_DEFAULT_OPERATOR_EMAIL"] = "operator@example.com"
        os.environ["MAGON_FOUNDATION_DEFAULT_OPERATOR_PASSWORD"] = "operator123"
        os.environ["MAGON_FOUNDATION_DEFAULT_CUSTOMER_EMAIL"] = "customer@example.com"
        os.environ["MAGON_FOUNDATION_DEFAULT_CUSTOMER_PASSWORD"] = "customer123"

        _apply_migrations(self.database_url)
        from magon_standalone.foundation.bootstrap import seed_foundation
        from magon_standalone.foundation.db import create_session_factory, session_scope
        from magon_standalone.foundation.settings import load_settings

        settings = load_settings()
        session_factory = create_session_factory(settings)
        with session_scope(session_factory) as session:
            seed_foundation(session, settings)

        self.client = TestClient(create_app())

    def tearDown(self):
        self.client.close()
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def _login(self, email: str, password: str) -> dict[str, str]:
        response = self.client.post("/api/v1/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200)
        return {"authorization": f"Bearer {response.json()['token']}"}

    def test_accepted_offer_creates_order_and_tracks_payment_and_audit(self):
        operator_headers = self._login("operator@example.com", "operator123")

        draft = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "order-flow@example.com",
                "customer_name": "Order Flow",
                "title": "Wave1 order flow",
                "summary": "Need order and internal payment lifecycle verification.",
                "item_service_context": "Custom packaging order that should move through partial readiness and payment updates.",
                "city": "Ho Chi Minh City",
                "requested_deadline_at": "2026-04-29T10:00:00+07:00",
                "intake_channel": "rfq_public",
                "honeypot": "",
                "elapsed_ms": 1800,
            },
        )
        draft_code = draft.json()["item"]["code"]
        submitted = self.client.post(
            f"/api/v1/public/draft-requests/{draft_code}/submit",
            json={"reason_code": "customer_submit_ready_draft"},
        )
        request_code = submitted.json()["request"]["code"]
        customer_ref = submitted.json()["request"]["customer_ref"]

        for target_status, reason_code in [
            ("needs_review", "operator_review_started"),
            ("supplier_search", "supplier_search_started"),
        ]:
            moved = self.client.post(
                f"/api/v1/operator/requests/{request_code}/transition",
                headers=operator_headers,
                json={"target_status": target_status, "reason_code": reason_code},
            )
            self.assertEqual(moved.status_code, 200)

        created_offer = self.client.post(
            f"/api/v1/operator/requests/{request_code}/offers",
            headers=operator_headers,
            json={
                "amount": 4100000,
                "currency_code": "VND",
                "lead_time_days": 10,
                "terms_text": "50% prepayment.",
                "scenario_type": "baseline",
                "supplier_ref": "SUPC-ORDER",
                "public_summary": "Order transition offer",
                "comparison_title": "Variant A",
                "comparison_rank": 1,
                "recommended": True,
                "highlights": ["Baseline", "Order check"],
                "reason_code": "offer_created_from_request",
            },
        )
        offer_code = created_offer.json()["offer"]["code"]

        self.client.post(
            f"/api/v1/operator/offers/{offer_code}/send",
            headers=operator_headers,
            json={"reason_code": "offer_sent_to_customer"},
        )
        self.client.post(
            f"/api/v1/public/requests/{customer_ref}/offers/{offer_code}/accept",
            json={"reason_code": "customer_acceptance_recorded"},
        )
        created_order = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/convert-to-order",
            headers=operator_headers,
            json={"reason_code": "confirmed_offer_converted_to_order"},
        )
        self.assertEqual(created_order.status_code, 200)
        order_code = created_order.json()["item"]["code"]
        self.assertEqual(created_order.json()["item"]["payment_state"], "created")
        self.assertEqual(created_order.json()["item"]["order_status"], "awaiting_payment")
        self.assertEqual(len(created_order.json()["lines"]), 1)
        payment_code = created_order.json()["payments"][0]["code"]
        line_code = created_order.json()["lines"][0]["code"]

        assign_supplier = self.client.post(
            f"/api/v1/operator/orders/{order_code}/action",
            headers=operator_headers,
            json={"action": "assign_supplier", "supplier_ref": "SUPC-ORDER", "reason_code": "order_supplier_assigned"},
        )
        self.assertEqual(assign_supplier.status_code, 200)
        self.assertIn("SUPC-ORDER", assign_supplier.json()["item"]["supplier_refs"])

        premature_start = self.client.post(
            f"/api/v1/operator/orders/{order_code}/action",
            headers=operator_headers,
            json={"action": "confirm_start", "reason_code": "order_start_confirmed"},
        )
        self.assertEqual(premature_start.status_code, 409)
        self.assertEqual(premature_start.json()["detail"], "order_payment_confirmation_required")

        payment_pending = self.client.post(
            f"/api/v1/operator/payment-records/{payment_code}/transition",
            headers=operator_headers,
            json={"target_state": "pending", "reason_code": "payment_pending_bank_transfer"},
        )
        self.assertEqual(payment_pending.status_code, 200)
        self.assertEqual(payment_pending.json()["order"]["payment_state"], "pending")

        payment_confirmed = self.client.post(
            f"/api/v1/operator/payment-records/{payment_code}/transition",
            headers=operator_headers,
            json={"target_state": "confirmed", "reason_code": "payment_confirmed_internal"},
        )
        self.assertEqual(payment_confirmed.status_code, 200)
        self.assertEqual(payment_confirmed.json()["order"]["payment_state"], "confirmed")
        self.assertEqual(payment_confirmed.json()["order"]["order_status"], "supplier_assigned")

        confirmed_start = self.client.post(
            f"/api/v1/operator/orders/{order_code}/action",
            headers=operator_headers,
            json={"action": "confirm_start", "reason_code": "order_start_confirmed"},
        )
        self.assertEqual(confirmed_start.status_code, 200)
        self.assertEqual(confirmed_start.json()["item"]["order_status"], "in_production")

        mark_production = self.client.post(
            f"/api/v1/operator/orders/{order_code}/action",
            headers=operator_headers,
            json={"action": "mark_production", "reason_code": "order_production_marked"},
        )
        self.assertEqual(mark_production.status_code, 200)
        self.assertEqual(mark_production.json()["item"]["order_status"], "in_production")

        ready = self.client.post(
            f"/api/v1/operator/orders/{order_code}/action",
            headers=operator_headers,
            json={"action": "ready", "reason_code": "order_ready_partial", "line_codes": [line_code]},
        )
        self.assertEqual(ready.status_code, 200)
        self.assertIn(ready.json()["item"]["readiness_state"], {"ready", "partial_ready"})

        payment_refund = self.client.post(
            f"/api/v1/operator/payment-records/{payment_code}/transition",
            headers=operator_headers,
            json={"target_state": "partially_refunded", "reason_code": "payment_partial_refund_manual"},
        )
        self.assertEqual(payment_refund.status_code, 200)
        self.assertEqual(payment_refund.json()["order"]["payment_state"], "partially_refunded")

        delivery = self.client.post(
            f"/api/v1/operator/orders/{order_code}/action",
            headers=operator_headers,
            json={"action": "delivery", "reason_code": "order_delivery_marked"},
        )
        self.assertEqual(delivery.status_code, 200)
        self.assertEqual(delivery.json()["item"]["logistics_state"], "delivered")
        completed = self.client.post(
            f"/api/v1/operator/orders/{order_code}/action",
            headers=operator_headers,
            json={"action": "complete", "reason_code": "order_completed_internal"},
        )
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["item"]["order_status"], "completed")

        disputed = self.client.post(
            f"/api/v1/operator/orders/{order_code}/action",
            headers=operator_headers,
            json={"action": "dispute", "reason_code": "order_dispute_opened"},
        )
        self.assertEqual(disputed.status_code, 200)
        self.assertEqual(disputed.json()["item"]["dispute_state"], "open")

        order_detail = self.client.get(f"/api/v1/operator/orders/{order_code}", headers=operator_headers)
        self.assertEqual(order_detail.status_code, 200)
        self.assertGreaterEqual(len(order_detail.json()["ledger"]), 3)

        request_view = self.client.get(f"/api/v1/public/requests/{customer_ref}")
        self.assertEqual(request_view.status_code, 200)
        self.assertEqual(request_view.json()["item"]["order"]["code"], order_code)

        audit_payload = self.client.get("/api/v1/operator/audit/events", headers=operator_headers)
        actions = {item["action"] for item in audit_payload.json()["items"]}
        self.assertIn("order_created", actions)
        self.assertIn("order_assign_supplier", actions)
        self.assertIn("payment_record_updated", actions)
        self.assertIn("order_complete", actions)
        self.assertIn("order_dispute", actions)


if __name__ == "__main__":
    unittest.main()
