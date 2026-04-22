from __future__ import annotations
# RU: Admin-config tests доказывают, что базовая business configuration теперь меняется через API, а не через правку seed-кода.

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


class TestFoundationAdminConfig(unittest.TestCase):
    def setUp(self) -> None:
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

    def tearDown(self) -> None:
        self.client.close()
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def _admin_headers(self) -> dict[str, str]:
        login = self.client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin123"})
        self.assertEqual(login.status_code, 200)
        return {"authorization": f"Bearer {login.json()['token']}"}

    def test_admin_can_configure_reason_rules_notifications_and_sources(self) -> None:
        headers = self._admin_headers()

        created_reason = self.client.post(
            "/api/v1/admin/reason-codes",
            json={
                "code": "config_guard_missing_spec",
                "title": "Не хватает спецификации",
                "category": "request",
                "severity": "warning",
                "default_visibility_scope": "internal",
                "description": "Оператору нужен полный набор спецификации.",
                "metadata_json": {"owner": "admin"},
                "is_active": True,
            },
            headers=headers,
        )
        self.assertEqual(created_reason.status_code, 200)

        updated_reason = self.client.patch(
            "/api/v1/admin/reason-codes/config_guard_missing_spec",
            json={
                "title": "Не хватает полной спецификации",
                "severity": "critical",
                "is_active": False,
                "metadata_json": {"owner": "ops"},
            },
            headers=headers,
        )
        self.assertEqual(updated_reason.status_code, 200)
        self.assertEqual(updated_reason.json()["item"]["severity"], "critical")
        self.assertFalse(updated_reason.json()["item"]["is_active"])

        created_rule = self.client.post(
            "/api/v1/admin/rules",
            json={
                "name": "Guard: request cannot leave review without files",
                "scope": "request_transition",
                "rule_kind": "transition_guard",
                "description": "Проверяет наличие файлов перед следующим переходом.",
                "enabled": True,
                "config_json": {"required_file_types": ["artwork"]},
                "metadata_json": {"owner": "admin"},
                "explainability_json": {"summary": "Нужен artwork перед переходом."},
            },
            headers=headers,
        )
        self.assertEqual(created_rule.status_code, 200)
        rule_code = created_rule.json()["item"]["code"]

        created_version = self.client.post(
            f"/api/v1/admin/rules/{rule_code}/versions",
            json={
                "version_status": "active",
                "metadata_json": {"revision": 2},
                "explainability_json": {"summary": "Ужесточили guard на отсутствие artwork."},
            },
            headers=headers,
        )
        self.assertEqual(created_version.status_code, 200)
        self.assertEqual(created_version.json()["item"]["version_no"], 2)

        created_notification = self.client.post(
            "/api/v1/admin/notification-rules",
            json={
                "event_type": "request_reason_added",
                "entity_type": "request",
                "recipient_scope": "internal",
                "channel": "inbox",
                "template_key": "request_blocker_internal",
                "min_interval_seconds": 900,
                "enabled": True,
                "rule_code": rule_code,
                "metadata_json": {"title": "Новый blocker по заявке"},
            },
            headers=headers,
        )
        self.assertEqual(created_notification.status_code, 200)
        notification_code = created_notification.json()["item"]["code"]

        updated_notification = self.client.patch(
            f"/api/v1/admin/notification-rules/{notification_code}",
            json={"recipient_scope": "customer", "enabled": False, "rule_code": ""},
            headers=headers,
        )
        self.assertEqual(updated_notification.status_code, 200)
        self.assertEqual(updated_notification.json()["item"]["recipient_scope"], "customer")
        self.assertFalse(updated_notification.json()["item"]["enabled"])

        created_source = self.client.post(
            "/api/v1/admin/supplier-sources",
            json={
                "label": "Manual config source",
                "adapter_key": "fixture_json",
                "config_json": {"schedule_enabled": False, "classification_mode": "deterministic_only"},
            },
            headers=headers,
        )
        self.assertEqual(created_source.status_code, 200)
        source_code = created_source.json()["item"]["code"]

        updated_source = self.client.patch(
            f"/api/v1/admin/supplier-sources/{source_code}",
            json={
                "label": "Manual config source updated",
                "enabled": False,
                "schedule_enabled": True,
                "schedule_interval_minutes": 120,
                "classification_mode": "ai_assisted_fallback",
                "config_json": {"schedule_enabled": True, "schedule_interval_minutes": 120, "classification_mode": "ai_assisted_fallback"},
            },
            headers=headers,
        )
        self.assertEqual(updated_source.status_code, 200)
        self.assertFalse(updated_source.json()["item"]["enabled"])
        self.assertEqual(updated_source.json()["item"]["schedule"]["interval_minutes"], 120)
        self.assertEqual(updated_source.json()["item"]["classification"]["mode"], "ai_assisted_fallback")

        rules_payload = self.client.get("/api/v1/operator/rules", headers=headers)
        notification_payload = self.client.get("/api/v1/admin/notification-rules", headers=headers)
        source_payload = self.client.get("/api/v1/operator/supplier-sources", headers=headers)
        reason_payload = self.client.get("/api/v1/operator/reason-codes", headers=headers)

        configured_rule = next(item for item in rules_payload.json()["items"] if item["code"] == rule_code)
        configured_notification = next(item for item in notification_payload.json()["items"] if item["code"] == notification_code)
        configured_source = next(item for item in source_payload.json()["items"] if item["code"] == source_code)
        configured_reason = next(item for item in reason_payload.json()["items"] if item["code"] == "config_guard_missing_spec")

        self.assertEqual(configured_rule["latest_version_no"], 2)
        self.assertIsNone(configured_notification["rule_code"])
        self.assertEqual(configured_source["schedule"]["interval_minutes"], 120)
        self.assertFalse(configured_reason["is_active"])


if __name__ == "__main__":
    unittest.main()
