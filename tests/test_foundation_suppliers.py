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


class TestFoundationSuppliers(unittest.TestCase):
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

    def test_supplier_import_normalize_dedup_verify_visible_in_admin(self):
        admin_headers = self._login("admin@example.com", "admin123")
        operator_headers = self._login("operator@example.com", "operator123")

        sources = self.client.get("/api/v1/operator/supplier-sources", headers=operator_headers)
        self.assertEqual(sources.status_code, 200)
        source_code = sources.json()["items"][0]["code"]

        baseline = self.client.post(
            "/api/v1/admin/suppliers",
            headers=admin_headers,
            json={
                "display_name": "Saigon Label Company",
                "address_text": "Thu Duc City, Ho Chi Minh City",
                "city": "Ho Chi Minh City",
                "district": "Thu Duc",
                "capability_summary": "LABEL_SELF_ADHESIVE",
                "capabilities_json": ["LABEL_SELF_ADHESIVE"],
                "reason_code": "test_seed_manual_supplier",
            },
        )
        self.assertEqual(baseline.status_code, 200)

        run_ingest = self.client.post(
            "/api/v1/operator/supplier-ingests/run-inline",
            headers=operator_headers,
            json={
                "source_registry_code": source_code,
                "idempotency_key": "fixture-batch-001",
                "reason_code": "test_fixture_ingest",
            },
        )
        self.assertEqual(run_ingest.status_code, 200)
        summary = run_ingest.json()["item"]
        self.assertEqual(summary["raw_count"], 3)
        self.assertEqual(summary["normalized_count"], 3)
        self.assertGreaterEqual(summary["merged_count"], 1)
        self.assertGreaterEqual(summary["candidate_count"], 1)

        raw_layer = self.client.get("/api/v1/operator/supplier-raw", headers=operator_headers)
        self.assertEqual(raw_layer.status_code, 200)
        self.assertEqual(len(raw_layer.json()["items"]), 3)

        candidates = self.client.get("/api/v1/operator/supplier-dedup-candidates", headers=operator_headers)
        self.assertEqual(candidates.status_code, 200)
        candidate = candidates.json()["items"][0]
        self.assertEqual(candidate["candidate_status"], "pending_review")

        resolved = self.client.post(
            f"/api/v1/operator/supplier-dedup-candidates/{candidate['code']}/decision",
            headers=operator_headers,
            json={"decision": "reject", "reason_code": "test_confirm_not_duplicate", "note": "Separate supplier"},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["item"]["candidate_status"], "rejected_as_duplicate")

        suppliers = self.client.get("/api/v1/operator/suppliers", headers=operator_headers)
        self.assertEqual(suppliers.status_code, 200)
        items = suppliers.json()["items"]
        minh_phat = next(item for item in items if "Minh Phat" in item["display_name"])

        contact_confirmed = self.client.post(
            f"/api/v1/operator/suppliers/{minh_phat['code']}/verify",
            headers=operator_headers,
            json={"target_trust_level": "contact_confirmed", "reason_code": "test_contact_confirmed"},
        )
        self.assertEqual(contact_confirmed.status_code, 200)
        capability_confirmed = self.client.post(
            f"/api/v1/operator/suppliers/{minh_phat['code']}/verify",
            headers=operator_headers,
            json={"target_trust_level": "capability_confirmed", "reason_code": "test_capability_confirmed"},
        )
        self.assertEqual(capability_confirmed.status_code, 200)
        trusted = self.client.post(
            f"/api/v1/operator/suppliers/{minh_phat['code']}/verify",
            headers=operator_headers,
            json={"target_trust_level": "trusted", "reason_code": "test_trusted"},
        )
        self.assertEqual(trusted.status_code, 200)
        self.assertEqual(trusted.json()["item"]["trust_level"], "trusted")

        detail = self.client.get(f"/api/v1/operator/suppliers/{minh_phat['code']}", headers=operator_headers)
        self.assertEqual(detail.status_code, 200)
        self.assertGreaterEqual(len(detail.json()["raw_records"]), 1)
        self.assertGreaterEqual(len(detail.json()["verification_history"]), 4)

        public_visible = self.client.get("/api/v1/public/suppliers")
        self.assertEqual(public_visible.status_code, 200)
        public_codes = {item["code"] for item in public_visible.json()["items"]}
        self.assertIn(minh_phat["code"], public_codes)

    def test_supplier_ingest_is_idempotent(self):
        operator_headers = self._login("operator@example.com", "operator123")
        source_code = self.client.get("/api/v1/operator/supplier-sources", headers=operator_headers).json()["items"][0]["code"]

        first = self.client.post(
            "/api/v1/operator/supplier-ingests/run-inline",
            headers=operator_headers,
            json={"source_registry_code": source_code, "idempotency_key": "fixture-batch-idempotent", "reason_code": "test_ingest_once"},
        )
        second = self.client.post(
            "/api/v1/operator/supplier-ingests/run-inline",
            headers=operator_headers,
            json={"source_registry_code": source_code, "idempotency_key": "fixture-batch-idempotent", "reason_code": "test_ingest_once"},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.json()["item"]["replayed"])
        self.assertTrue(second.json()["item"]["replayed"])
        self.assertEqual(first.json()["item"]["ingest_code"], second.json()["item"]["ingest_code"])

        ingests = self.client.get("/api/v1/operator/supplier-ingests", headers=operator_headers)
        self.assertEqual(ingests.status_code, 200)
        self.assertEqual(len(ingests.json()["items"]), 1)


if __name__ == "__main__":
    unittest.main()
