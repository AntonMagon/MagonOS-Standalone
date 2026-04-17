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


class TestFoundationEventsDashboards(unittest.TestCase):
    # RU: Acceptance-цепочка проверяет event emission, visibility, notification rules и dashboard counters за один прогон.
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

    def _create_request(self) -> tuple[str, str]:
        created = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "timeline@example.com",
                "customer_name": "Timeline Demo",
                "title": "Сквозной timeline request",
                "summary": "Нужен проверяемый контур notifications и dashboards.",
                "item_service_context": "Коммерческий intake для проверки правил и уведомлений.",
                "city": "Ho Chi Minh City",
                "requested_deadline_at": "2026-05-02T11:00:00+07:00",
                "intake_channel": "rfq_public",
                "honeypot": "",
                "elapsed_ms": 1900,
            },
        )
        self.assertEqual(created.status_code, 200)
        draft_code = created.json()["item"]["code"]
        submitted = self.client.post(
            f"/api/v1/public/draft-requests/{draft_code}/submit",
            json={"reason_code": "customer_submit_ready_draft"},
        )
        self.assertEqual(submitted.status_code, 200)
        return submitted.json()["request"]["code"], submitted.json()["request"]["customer_ref"]

    def test_notifications_visibility_and_dashboard_metrics(self):
        operator_headers = self._login("operator@example.com", "operator123")
        admin_headers = self._login("admin@example.com", "admin123")
        request_code, customer_ref = self._create_request()

        review = self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            headers=operator_headers,
            json={"target_status": "needs_review", "reason_code": "operator_review_started"},
        )
        self.assertEqual(review.status_code, 200)

        clarification = self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            headers=operator_headers,
            json={
                "target_status": "needs_clarification",
                "reason_code": "customer_clarification_needed",
                "note": "Нужно дозапросить artwork и тираж.",
            },
        )
        self.assertEqual(clarification.status_code, 200)

        blocker = self.client.post(
            f"/api/v1/operator/requests/{request_code}/reasons",
            headers=operator_headers,
            json={
                "reason_kind": "blocker",
                "reason_code": "missing_artwork",
                "note": "Макет пока не приложен.",
            },
        )
        self.assertEqual(blocker.status_code, 200)

        customer_dashboard = self.client.get(f"/api/v1/public/requests/{customer_ref}/dashboard")
        customer_notifications = self.client.get(f"/api/v1/public/requests/{customer_ref}/notifications")
        operator_workbench = self.client.get("/api/v1/operator/workbench", headers=operator_headers)
        processing_dashboard = self.client.get("/api/v1/operator/dashboard/processing", headers=operator_headers)
        operator_timeline = self.client.get(f"/api/v1/operator/timeline/request/{request_code}", headers=operator_headers)
        admin_dashboard = self.client.get("/api/v1/admin/dashboard", headers=admin_headers)

        self.assertEqual(customer_dashboard.status_code, 200)
        self.assertEqual(customer_notifications.status_code, 200)
        self.assertEqual(operator_workbench.status_code, 200)
        self.assertEqual(processing_dashboard.status_code, 200)
        self.assertEqual(operator_timeline.status_code, 200)
        self.assertEqual(admin_dashboard.status_code, 200)

        customer_notification_items = customer_notifications.json()["items"]
        self.assertNotIn("owner_user_id", customer_dashboard.json()["request"])
        self.assertNotIn("customer_email", customer_dashboard.json()["request"])
        self.assertTrue(
            any(item["reason_code"] == "customer_clarification_needed" for item in customer_notification_items),
            "customer should see clarification notification",
        )
        self.assertFalse(
            any(item["reason_code"] == "missing_artwork" for item in customer_notification_items),
            "customer should not see internal blocker notification",
        )

        workbench_payload = operator_workbench.json()
        self.assertTrue(any(item["reason_code"] == "missing_artwork" for item in workbench_payload["notifications"]))
        self.assertTrue(any(item["owner_code"] == request_code for item in workbench_payload["blocked_items"]))

        processing_payload = processing_dashboard.json()
        self.assertEqual(processing_payload["requests_by_status"]["needs_clarification"], 1)
        self.assertTrue(any(item["owner_code"] == request_code for item in processing_payload["blocked_items"]))

        timeline_items = operator_timeline.json()["items"]
        self.assertTrue(any(item["entry_kind"] == "event" and item["reason_code"] == "customer_clarification_needed" for item in timeline_items))
        self.assertTrue(any(item["entry_kind"] == "notification" and item["reason_code"] == "missing_artwork" for item in timeline_items))

        admin_counts = admin_dashboard.json()["counts"]
        self.assertGreaterEqual(admin_counts["message_events"], 1)
        self.assertGreaterEqual(admin_counts["notifications"], 1)

    def test_public_request_payload_hides_internal_fields(self):
        operator_headers = self._login("operator@example.com", "operator123")
        request_code, customer_ref = self._create_request()

        self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            headers=operator_headers,
            json={"target_status": "needs_review", "reason_code": "operator_review_started"},
        )
        self.client.post(
            f"/api/v1/operator/requests/{request_code}/follow-up-items",
            headers=operator_headers,
            json={
                "title": "Прислать тираж",
                "detail": "Клиенту нужно подтвердить финальный объём.",
                "customer_visible": True,
                "reason_code": "clarification_follow_up_created",
            },
        )
        self.client.post(
            f"/api/v1/operator/requests/{request_code}/reasons",
            headers=operator_headers,
            json={
                "reason_kind": "reason",
                "reason_code": "customer_clarification_needed",
                "note": "Нужна дополнительная коммерческая информация.",
            },
        )

        public_response = self.client.get(f"/api/v1/public/requests/{customer_ref}")
        self.assertEqual(public_response.status_code, 200)
        item = public_response.json()["item"]

        self.assertNotIn("owner_user_id", item)
        self.assertNotIn("assignee_user_id", item)
        self.assertNotIn("customer_email", item)

        self.assertTrue(item["reasons"])
        self.assertNotIn("created_by_user_id", item["reasons"][0])
        self.assertNotIn("resolved_by_user_id", item["reasons"][0])

        self.assertTrue(item["follow_up_items"])
        self.assertNotIn("owner_user_id", item["follow_up_items"][0])

        if item["managed_files"]:
            self.assertNotIn("owner_id", item["managed_files"][0])
            self.assertNotIn("uploaded_by_user_id", item["managed_files"][0])

        if item["documents"]:
            self.assertNotIn("owner_id", item["documents"][0])
            self.assertNotIn("created_by_user_id", item["documents"][0])


if __name__ == "__main__":
    unittest.main()
