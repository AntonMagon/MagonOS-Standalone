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


def _apply_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    os.environ["MAGON_FOUNDATION_DATABASE_URL"] = database_url
    command.upgrade(config, "head")


class TestFoundationApi(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite+pysqlite:///{Path(self.tmpdir.name) / 'foundation.sqlite3'}"
        self.legacy_db_path = str(Path(self.tmpdir.name) / "legacy.sqlite3")
        self._previous = {key: os.environ.get(key) for key in [
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
        ]}
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

    def test_health_and_login_flow(self):
        live = self.client.get("/health/live")
        ready = self.client.get("/health/ready")
        legacy_status = self.client.get("/status")

        self.assertEqual(live.status_code, 200)
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ok")
        self.assertEqual(legacy_status.status_code, 404)

        login = self.client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"})
        self.assertEqual(login.status_code, 200)
        token = login.json()["token"]

        me = self.client.get("/api/v1/auth/me", headers={"authorization": f"Bearer {token}"})
        dashboard = self.client.get("/api/v1/operator/dashboard/summary", headers={"authorization": f"Bearer {token}"})

        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.json()["authenticated"])
        self.assertEqual(dashboard.status_code, 200)
        self.assertGreaterEqual(dashboard.json()["counts"]["users"], 3)

    def test_draft_request_offer_order_transition_audit(self):
        operator_login = self.client.post("/api/v1/auth/login", json={"email": "operator@example.com", "password": "operator123"})
        operator_token = operator_login.json()["token"]
        headers = {"authorization": f"Bearer {operator_token}"}

        company_list = self.client.get("/api/v1/operator/companies", headers=headers)
        company_code = company_list.json()["items"][0]["code"]

        created_draft = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "buyer@example.com",
                "customer_name": "Buyer",
                "customer_phone": "+84909000111",
                "guest_company_name": "Buyer Co",
                "company_code": company_code,
                "title": "Need sample packaging",
                "summary": "Need first-wave packaging slot and intake check.",
                "item_service_context": "Need custom corrugated transport packaging with manual supplier review.",
                "city": "Ho Chi Minh City",
                "requested_deadline_at": "2026-04-25T10:00:00+07:00",
                "intake_channel": "web_public",
                "locale_code": "ru",
                "honeypot": "",
                "elapsed_ms": 1600,
            },
        )
        self.assertEqual(created_draft.status_code, 200)
        draft_code = created_draft.json()["item"]["code"]
        self.assertEqual(created_draft.json()["item"]["draft_status"], "ready_to_submit")

        submitted = self.client.post(
            f"/api/v1/public/draft-requests/{draft_code}/submit",
            json={"reason_code": "customer_submit_ready_draft", "note": "Customer submitted request from draft."},
        )
        self.assertEqual(submitted.status_code, 200)
        request_code = submitted.json()["request"]["code"]
        self.assertEqual(submitted.json()["request"]["request_status"], "new")

        review = self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            json={"target_status": "needs_review", "reason_code": "operator_review_started", "note": "Operator started review."},
            headers=headers,
        )
        self.assertEqual(review.status_code, 200)

        supplier_search = self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            json={"target_status": "supplier_search", "reason_code": "supplier_search_started", "note": "Operator moved request to supplier search."},
            headers=headers,
        )
        self.assertEqual(supplier_search.status_code, 200)

        created_offer = self.client.post(
            f"/api/v1/operator/requests/{request_code}/offers",
            json={
                "amount": 4200000,
                "currency_code": "VND",
                "lead_time_days": 9,
                "terms_text": "50% prepayment after confirmation.",
                "scenario_type": "baseline",
                "public_summary": "Wave1 offer",
                "comparison_title": "Baseline",
                "comparison_rank": 1,
                "reason_code": "pricing_ready",
                "note": "Operator prepared offer.",
            },
            headers=headers,
        )
        self.assertEqual(created_offer.status_code, 200)
        offer_code = created_offer.json()["offer"]["code"]

        sent_offer = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/send",
            json={"reason_code": "offer_sent_to_customer", "note": "Offer was sent to customer."},
            headers=headers,
        )
        self.assertEqual(sent_offer.status_code, 200)

        accepted_offer = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/accept",
            json={"reason_code": "customer_acceptance_recorded", "note": "Customer accepted offer."},
            headers=headers,
        )
        self.assertEqual(accepted_offer.status_code, 200)
        self.assertEqual(accepted_offer.json()["offer"]["confirmation_state"], "accepted")

        created_order = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/convert-to-order",
            json={"reason_code": "confirmed_offer_converted_to_order", "note": "Confirmed version converted to order."},
            headers=headers,
        )
        self.assertEqual(created_order.status_code, 200)

        requests_payload = self.client.get("/api/v1/operator/requests", headers=headers)
        orders_payload = self.client.get("/api/v1/operator/orders", headers=headers)
        audit_payload = self.client.get("/api/v1/operator/audit/events", headers=headers)
        request_items = requests_payload.json()["items"]
        request_item = next(item for item in request_items if item["code"] == request_code)

        self.assertEqual(requests_payload.status_code, 200)
        self.assertEqual(orders_payload.status_code, 200)
        self.assertEqual(orders_payload.json()["items"][0]["public_status"], "accepted")
        self.assertEqual(request_item["request_status"], "converted_to_order")
        actions = {item["action"] for item in audit_payload.json()["items"]}
        self.assertIn("draft_submitted", actions)
        self.assertIn("offer_created", actions)
        self.assertIn("offer_sent", actions)
        self.assertIn("offer_accepted", actions)
        self.assertIn("order_created", actions)

    def test_role_restrictions_enforced(self):
        operator_login = self.client.post("/api/v1/auth/login", json={"email": "operator@example.com", "password": "operator123"})
        customer_login = self.client.post("/api/v1/auth/login", json={"email": "customer@example.com", "password": "customer123"})

        operator_headers = {"authorization": f"Bearer {operator_login.json()['token']}"}
        customer_headers = {"authorization": f"Bearer {customer_login.json()['token']}"}

        admin_only = self.client.get("/api/v1/admin/users", headers=operator_headers)
        operator_only = self.client.get("/api/v1/operator/requests", headers=customer_headers)
        public_only = self.client.get("/api/v1/operator/requests")

        self.assertEqual(admin_only.status_code, 403)
        self.assertEqual(operator_only.status_code, 403)
        self.assertEqual(public_only.status_code, 401)

    def test_legacy_bridge_is_opt_in(self):
        os.environ["MAGON_FOUNDATION_LEGACY_ENABLED"] = "true"
        legacy_client = TestClient(create_app())
        try:
            legacy_status = legacy_client.get("/status")
            self.assertEqual(legacy_status.status_code, 200)
        finally:
            legacy_client.close()


if __name__ == "__main__":
    unittest.main()
