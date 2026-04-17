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


class TestFoundationDraftRequest(unittest.TestCase):
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

    def test_draft_blocks_submit_until_required_fields_are_filled(self):
        created = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "draft@example.com",
                "title": "Черновик без дедлайна",
                "summary": "Пока неполный draft для проверки blocking guard.",
                "intake_channel": "web_public",
                "honeypot": "",
                "elapsed_ms": 1800,
            },
        )
        self.assertEqual(created.status_code, 200)
        draft = created.json()["item"]
        draft_code = draft["code"]
        self.assertEqual(draft["draft_status"], "awaiting_data")

        blocked_submit = self.client.post(
            f"/api/v1/public/draft-requests/{draft_code}/submit",
            json={"reason_code": "customer_submit_ready_draft"},
        )
        self.assertEqual(blocked_submit.status_code, 422)
        self.assertEqual(blocked_submit.json()["detail"], "draft_required_fields_missing")

        updated = self.client.patch(
            f"/api/v1/public/draft-requests/{draft_code}",
            json={
                "customer_name": "Draft User",
                "item_service_context": "Нужен расчёт по упаковке для ручного review.",
                "city": "Ho Chi Minh City",
                "requested_deadline_at": "2026-04-26T11:00:00+07:00",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["item"]["draft_status"], "ready_to_submit")

        link = self.client.post(
            f"/api/v1/public/draft-requests/{draft_code}/file-links",
            json={
                "label": "Google Drive brief",
                "file_url": "https://example.com/brief.pdf",
                "visibility": "role",
                "reason_code": "customer_file_link_added",
            },
        )
        self.assertEqual(link.status_code, 200)

        submitted = self.client.post(
            f"/api/v1/public/draft-requests/{draft_code}/submit",
            json={"reason_code": "customer_submit_ready_draft", "note": "Ready to submit after completing required fields."},
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["draft"]["draft_status"], "archived")
        self.assertEqual(submitted.json()["request"]["request_status"], "new")
        self.assertIsNotNone(submitted.json()["request"]["customer_ref"])

    def test_request_blocker_prevents_forward_transition_until_resolved(self):
        operator_headers = self._login("operator@example.com", "operator123")
        created = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "ops@example.com",
                "customer_name": "Ops Demo",
                "title": "Нужна упаковка и образцы",
                "summary": "Request flow guard test.",
                "item_service_context": "Индивидуальная упаковка с ручным supplier search.",
                "city": "Da Nang",
                "requested_deadline_at": "2026-04-29T14:00:00+07:00",
                "intake_channel": "rfq_public",
                "honeypot": "",
                "elapsed_ms": 2000,
            },
        )
        draft_code = created.json()["item"]["code"]
        submitted = self.client.post(
            f"/api/v1/public/draft-requests/{draft_code}/submit",
            json={"reason_code": "customer_submit_ready_draft"},
        )
        request_code = submitted.json()["request"]["code"]

        review = self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            headers=operator_headers,
            json={"target_status": "needs_review", "reason_code": "operator_review_started"},
        )
        self.assertEqual(review.status_code, 200)

        blocker = self.client.post(
            f"/api/v1/operator/requests/{request_code}/reasons",
            headers=operator_headers,
            json={"reason_kind": "blocker", "reason_code": "missing_artwork", "note": "Artwork file is still missing."},
        )
        self.assertEqual(blocker.status_code, 200)
        blocker_code = blocker.json()["item"]["code"]

        blocked_transition = self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            headers=operator_headers,
            json={"target_status": "supplier_search", "reason_code": "supplier_search_started"},
        )
        self.assertEqual(blocked_transition.status_code, 409)
        self.assertEqual(blocked_transition.json()["detail"], "request_has_active_blockers")

        clarification = self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            headers=operator_headers,
            json={"target_status": "needs_clarification", "reason_code": "customer_clarification_needed", "note": "Need artwork and final dieline."},
        )
        self.assertEqual(clarification.status_code, 200)

        follow_up = self.client.post(
            f"/api/v1/operator/requests/{request_code}/follow-up-items",
            headers=operator_headers,
            json={
                "title": "Прислать artwork",
                "detail": "Клиент должен прислать финальный artwork файл.",
                "customer_visible": True,
                "reason_code": "clarification_follow_up_created",
            },
        )
        self.assertEqual(follow_up.status_code, 200)
        self.assertEqual(follow_up.json()["item"]["follow_up_status"], "waiting_customer")

        resolved = self.client.post(
            f"/api/v1/operator/request-reasons/{blocker_code}/resolve",
            headers=operator_headers,
            json={"reason_code": "customer_artwork_received"},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertFalse(resolved.json()["item"]["is_active"])

        moved = self.client.post(
            f"/api/v1/operator/requests/{request_code}/transition",
            headers=operator_headers,
            json={"target_status": "supplier_search", "reason_code": "supplier_search_started"},
        )
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()["item"]["request_status"], "supplier_search")

        customer_view = self.client.get(f"/api/v1/public/requests/{submitted.json()['request']['customer_ref']}")
        self.assertEqual(customer_view.status_code, 200)
        self.assertEqual(len(customer_view.json()["item"]["follow_up_items"]), 1)


if __name__ == "__main__":
    unittest.main()
