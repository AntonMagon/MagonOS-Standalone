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


# RU: Offer-тесты всегда поднимают схему с нуля, чтобы versioned flow не зависел от локальной БД разработчика.
def _apply_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    os.environ["MAGON_FOUNDATION_DATABASE_URL"] = database_url
    command.upgrade(config, "head")


class TestFoundationOffers(unittest.TestCase):
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

    def test_versioned_offer_flow_requires_confirmed_current_version_for_order(self):
        operator_headers = self._login("operator@example.com", "operator123")

        draft = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "offer-flow@example.com",
                "customer_name": "Offer Flow",
                "title": "Versioned commercial offer flow",
                "summary": "Need versioned offer flow verification.",
                "item_service_context": "Custom packaging with multiple commercial variants.",
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
                "supplier_ref": "SUPC-TEST",
                "public_summary": "Offer version 1",
                "comparison_title": "Variant A",
                "comparison_rank": 1,
                "recommended": True,
                "highlights": ["Baseline", "10 day lead time"],
                "reason_code": "offer_created_from_request",
            },
        )
        self.assertEqual(created_offer.status_code, 200)
        offer_code = created_offer.json()["offer"]["code"]
        self.assertEqual(created_offer.json()["current_version"]["version_no"], 1)

        sent_v1 = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/send",
            headers=operator_headers,
            json={"reason_code": "offer_sent_to_customer"},
        )
        self.assertEqual(sent_v1.status_code, 200)
        self.assertEqual(sent_v1.json()["offer"]["offer_status"], "awaiting_confirmation")

        accepted_v1 = self.client.post(
            f"/api/v1/public/requests/{customer_ref}/offers/{offer_code}/accept",
            json={"reason_code": "customer_acceptance_recorded"},
        )
        self.assertEqual(accepted_v1.status_code, 200)
        self.assertEqual(accepted_v1.json()["offer"]["confirmation_state"], "accepted")

        revised_v2 = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/revise",
            headers=operator_headers,
            json={
                "amount": 4450000,
                "currency_code": "VND",
                "lead_time_days": 12,
                "terms_text": "50% prepayment after confirmation, balance before shipment.",
                "scenario_type": "revised",
                "supplier_ref": "SUPC-TEST",
                "public_summary": "Offer version 2",
                "comparison_title": "Variant A revised",
                "comparison_rank": 1,
                "recommended": True,
                "highlights": ["Revised specs", "12 day lead time"],
                "reason_code": "offer_critical_revision",
            },
        )
        self.assertEqual(revised_v2.status_code, 200)
        self.assertEqual(revised_v2.json()["current_version"]["version_no"], 2)
        self.assertEqual(revised_v2.json()["offer"]["confirmation_state"], "pending")

        detail = self.client.get(f"/api/v1/operator/offers/{offer_code}", headers=operator_headers)
        self.assertEqual(detail.status_code, 200)
        detail_payload = detail.json()
        version_map = {item["version_no"]: item for item in detail_payload["versions"]}
        self.assertEqual(version_map[1]["confirmation_state"], "accepted")
        self.assertEqual(version_map[1]["version_status"], "superseded")
        self.assertEqual(version_map[2]["confirmation_state"], "pending")
        self.assertTrue(any(item["confirmation_action"] == "reset_invalidated" for item in detail_payload["confirmations"]))
        self.assertEqual(len(detail_payload["reset_reasons"]), 1)

        premature_order = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/convert-to-order",
            headers=operator_headers,
            json={"reason_code": "confirmed_offer_converted_to_order"},
        )
        self.assertEqual(premature_order.status_code, 409)
        self.assertEqual(premature_order.json()["detail"], "offer_version_not_confirmed")

        resent_v2 = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/send",
            headers=operator_headers,
            json={"reason_code": "offer_sent_to_customer"},
        )
        self.assertEqual(resent_v2.status_code, 200)

        accepted_v2 = self.client.post(
            f"/api/v1/public/requests/{customer_ref}/offers/{offer_code}/accept",
            json={"reason_code": "customer_acceptance_recorded"},
        )
        self.assertEqual(accepted_v2.status_code, 200)
        self.assertEqual(accepted_v2.json()["current_version"]["version_no"], 2)
        self.assertEqual(accepted_v2.json()["offer"]["confirmation_state"], "accepted")

        compare_payload = self.client.get(f"/api/v1/public/requests/{customer_ref}/offers/compare")
        self.assertEqual(compare_payload.status_code, 200)
        self.assertEqual(len(compare_payload.json()["items"]), 1)
        self.assertEqual(compare_payload.json()["items"][0]["current_version"]["version_no"], 2)

        created_order = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/convert-to-order",
            headers=operator_headers,
            json={"reason_code": "confirmed_offer_converted_to_order"},
        )
        self.assertEqual(created_order.status_code, 200)
        self.assertIsNotNone(created_order.json()["item"]["offer_version_id"])


if __name__ == "__main__":
    unittest.main()
