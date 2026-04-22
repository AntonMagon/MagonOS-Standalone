# RU: Файл входит в проверенный контур первой волны.
# RU: Catalog tests держат публичный showcase contour внутри того же foundation runtime, что и операторские экраны.
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


class TestFoundationCatalog(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite+pysqlite:///{Path(self.tmpdir.name) / 'foundation.sqlite3'}"
        self._previous = {
            key: os.environ.get(key)
            for key in [
                "MAGON_ENV",
                "MAGON_FOUNDATION_DATABASE_URL",
                "MAGON_FOUNDATION_REDIS_URL",
                "MAGON_FOUNDATION_CELERY_BROKER_URL",
                "MAGON_FOUNDATION_CELERY_RESULT_BACKEND",
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

    def test_guest_can_browse_catalog_start_draft_and_submit_rfq(self):
        directions = self.client.get("/api/v1/public/catalog/directions")
        self.assertEqual(directions.status_code, 200)
        self.assertGreaterEqual(len(directions.json()["items"]), 3)

        showcase = self.client.get("/api/v1/public/catalog/items")
        self.assertEqual(showcase.status_code, 200)
        self.assertGreaterEqual(len(showcase.json()["items"]), 3)
        ready_item = next(item for item in showcase.json()["items"] if item["mode"] == "ready")
        rfq_item = next(item for item in showcase.json()["items"] if item["mode"] == "rfq")

        detail = self.client.get(f"/api/v1/public/catalog/items/{ready_item['code']}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["item"]["code"], ready_item["code"])
        self.assertIn("en", detail.json()["item"]["translations"])

        quick_draft = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "guest@example.com",
                "customer_name": "Guest Buyer",
                "customer_phone": "+84909000999",
                "guest_company_name": "Guest Brand",
                "catalog_item_code": ready_item["code"],
                "title": f"Хочу обсудить {ready_item['title']}",
                "summary": "Нужен быстрый расчёт по базовой карточке витрины.",
                "item_service_context": ready_item["title"],
                "city": "Ho Chi Minh City",
                "requested_deadline_at": "2026-04-24T09:00:00+07:00",
                "intake_channel": "catalog_ready",
                "locale_code": "ru",
                "honeypot": "",
                "elapsed_ms": 1800,
            },
        )
        self.assertEqual(quick_draft.status_code, 200)
        quick_draft_code = quick_draft.json()["item"]["code"]
        self.assertEqual(quick_draft.json()["item"]["draft_status"], "ready_to_submit")

        submitted_quick = self.client.post(
            f"/api/v1/public/draft-requests/{quick_draft_code}/submit",
            json={"reason_code": "catalog_guest_intake_verified", "note": "Guest submitted showcase draft."},
        )
        self.assertEqual(submitted_quick.status_code, 200)
        self.assertIsNotNone(submitted_quick.json()["request"]["catalog_item_id"])
        self.assertIsNotNone(submitted_quick.json()["request"]["customer_ref"])

        rfq_draft = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "rfq@example.com",
                "customer_name": "RFQ Buyer",
                "customer_phone": "+84909000888",
                "guest_company_name": "Complex Project Co",
                "catalog_item_code": rfq_item["code"],
                "title": "Сложный RFQ по упаковке",
                "summary": "Нужен кастомный расчёт по нестандартному проекту с образцами.",
                "item_service_context": "Нужен сложный RFQ по упаковке, образцам и ручной проверке производства.",
                "city": "Da Nang",
                "requested_deadline_at": "2026-04-28T15:30:00+07:00",
                "intake_channel": "rfq_public",
                "locale_code": "en",
                "honeypot": "",
                "elapsed_ms": 2200,
            },
        )
        self.assertEqual(rfq_draft.status_code, 200)
        self.assertEqual(rfq_draft.json()["item"]["intake_channel"], "rfq_public")
        rfq_draft_code = rfq_draft.json()["item"]["code"]

        submitted_rfq = self.client.post(
            f"/api/v1/public/draft-requests/{rfq_draft_code}/submit",
            json={"reason_code": "rfq_entry_point_verified", "note": "Guest submitted RFQ draft."},
        )
        self.assertEqual(submitted_rfq.status_code, 200)
        self.assertEqual(submitted_rfq.json()["request"]["locale_code"], "en")
        self.assertIsNotNone(submitted_rfq.json()["request"]["catalog_item_id"])
        customer_ref = submitted_rfq.json()["request"]["customer_ref"]

        customer_request = self.client.get(f"/api/v1/public/requests/{customer_ref}")
        self.assertEqual(customer_request.status_code, 200)
        self.assertEqual(customer_request.json()["item"]["request_status"], "new")

    def test_public_form_antibot_blocks_fast_submit(self):
        showcase = self.client.get("/api/v1/public/catalog/items")
        item_code = showcase.json()["items"][0]["code"]

        rejected = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "bot@example.com",
                "catalog_item_code": item_code,
                "title": "bot",
                "summary": "bot summary attempt",
                "honeypot": "",
                "elapsed_ms": 250,
            },
        )
        self.assertEqual(rejected.status_code, 422)
        self.assertEqual(rejected.json()["detail"], "antibot_elapsed_too_short")


if __name__ == "__main__":
    unittest.main()
