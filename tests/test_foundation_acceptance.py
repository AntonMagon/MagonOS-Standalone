# RU: Файл фиксирует приемочные и эксплуатационные риски первой волны, а не только счастливые сценарии.
# RU: Acceptance contour должен оставаться explainable даже после вырезания active legacy drift.
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from magon_standalone.foundation.app import create_app


def _apply_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    os.environ["MAGON_FOUNDATION_DATABASE_URL"] = database_url
    command.upgrade(config, "head")


class TestFoundationAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite+pysqlite:///{Path(self.tmpdir.name) / 'foundation.sqlite3'}"
        self.storage_root = str(Path(self.tmpdir.name) / "storage")
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
                "MAGON_FOUNDATION_STORAGE_BACKEND",
                "MAGON_FOUNDATION_STORAGE_LOCAL_ROOT",
                "MAGON_FOUNDATION_SYSTEM_MODE",
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
        os.environ["MAGON_FOUNDATION_STORAGE_BACKEND"] = "local"
        os.environ["MAGON_FOUNDATION_STORAGE_LOCAL_ROOT"] = self.storage_root
        os.environ["MAGON_FOUNDATION_SYSTEM_MODE"] = "test"

        _apply_migrations(self.database_url)
        from magon_standalone.foundation.bootstrap import seed_foundation
        from magon_standalone.foundation.db import create_session_factory, session_scope
        from magon_standalone.foundation.settings import load_settings

        settings = load_settings()
        session_factory = create_session_factory(settings)
        with session_scope(session_factory) as session:
            seed_foundation(session, settings)

        self.client = TestClient(create_app(), raise_server_exceptions=False)

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
        draft = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "acceptance@example.com",
                "customer_name": "Acceptance Demo",
                "title": "Wave1 acceptance request",
                "summary": "Need acceptance coverage for files, docs and dashboards.",
                "item_service_context": "Managed files/documents and versioned offer flow.",
                "city": "Ho Chi Minh City",
                "requested_deadline_at": "2026-05-03T09:00:00+07:00",
                "intake_channel": "rfq_public",
                "honeypot": "",
                "elapsed_ms": 2300,
            },
        )
        self.assertEqual(draft.status_code, 200)
        submitted = self.client.post(
            f"/api/v1/public/draft-requests/{draft.json()['item']['code']}/submit",
            json={"reason_code": "customer_submit_ready_draft"},
        )
        self.assertEqual(submitted.status_code, 200)
        return submitted.json()["request"]["code"], submitted.json()["request"]["customer_ref"]

    def _create_offer(self, request_code: str, customer_ref: str, operator_headers: dict[str, str]) -> str:
        for target_status, reason_code in [
            ("needs_review", "operator_review_started"),
            ("supplier_search", "supplier_search_started"),
        ]:
            response = self.client.post(
                f"/api/v1/operator/requests/{request_code}/transition",
                headers=operator_headers,
                json={"target_status": target_status, "reason_code": reason_code},
            )
            self.assertEqual(response.status_code, 200)
        created_offer = self.client.post(
            f"/api/v1/operator/requests/{request_code}/offers",
            headers=operator_headers,
            json={
                "amount": 3100000,
                "currency_code": "VND",
                "lead_time_days": 8,
                "terms_text": "50% prepayment.",
                "scenario_type": "baseline",
                "supplier_ref": "SUPC-ACC",
                "public_summary": "Acceptance offer",
                "comparison_title": "Acceptance baseline",
                "comparison_rank": 1,
                "reason_code": "offer_created_from_request",
            },
        )
        self.assertEqual(created_offer.status_code, 200)
        offer_code = created_offer.json()["offer"]["code"]
        sent = self.client.post(
            f"/api/v1/operator/offers/{offer_code}/send",
            headers=operator_headers,
            json={"reason_code": "offer_sent_to_customer"},
        )
        self.assertEqual(sent.status_code, 200)
        accepted = self.client.post(
            f"/api/v1/public/requests/{customer_ref}/offers/{offer_code}/accept",
            json={"reason_code": "customer_acceptance_recorded"},
        )
        self.assertEqual(accepted.status_code, 200)
        return offer_code

    def test_maintenance_mode_blocks_mutations_but_preserves_health_and_reads(self):
        self.client.close()
        os.environ["MAGON_FOUNDATION_SYSTEM_MODE"] = "maintenance"
        self.client = TestClient(create_app(), raise_server_exceptions=False)

        live = self.client.get("/health/live")
        self.assertEqual(live.status_code, 200)
        self.assertEqual(live.json()["system_mode"], "maintenance")

        meta = self.client.get("/api/v1/meta/system-mode")
        self.assertEqual(meta.status_code, 200)
        self.assertTrue(meta.json()["write_blocked"])

        catalog = self.client.get("/api/v1/public/catalog/items")
        self.assertEqual(catalog.status_code, 200)

        blocked = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "blocked@example.com",
                "title": "Blocked by maintenance",
                "summary": "Should not be created while maintenance mode is active.",
                "intake_channel": "web_public",
                "honeypot": "",
                "elapsed_ms": 1500,
            },
        )
        self.assertEqual(blocked.status_code, 503)
        self.assertEqual(blocked.json()["detail"], "system_in_maintenance_mode")

    def test_supplier_ingest_failure_is_visible_and_retryable(self):
        admin_headers = self._login("admin@example.com", "admin123")
        operator_headers = self._login("operator@example.com", "operator123")

        failing_source = self.client.post(
            "/api/v1/admin/supplier-sources",
            headers=admin_headers,
            json={
                "label": "Fixture failure source",
                "adapter_key": "fixture_json",
                "config_json": {"force_error": "fixture adapter exploded", "source_label": "failing_fixture"},
                "reason_code": "admin_create_supplier_source",
            },
        )
        self.assertEqual(failing_source.status_code, 200)
        source_code = failing_source.json()["item"]["code"]

        failed = self.client.post(
            "/api/v1/operator/supplier-ingests/run-inline",
            headers=operator_headers,
            json={
                "source_registry_code": source_code,
                "idempotency_key": "acceptance-failing-ingest",
                "reason_code": "test_ingest_failure",
            },
        )
        self.assertEqual(failed.status_code, 500)

        ingests = self.client.get("/api/v1/operator/supplier-ingests", headers=operator_headers)
        self.assertEqual(ingests.status_code, 200)
        failed_ingest = next(item for item in ingests.json()["items"] if item["idempotency_key"] == "acceptance-failing-ingest")
        self.assertEqual(failed_ingest["ingest_status"], "failed")
        self.assertEqual(failed_ingest["failure_code"], "RuntimeError")
        self.assertTrue(failed_ingest["retry_allowed"])
        ingest_code = failed_ingest["code"]

        from magon_standalone.foundation.db import create_session_factory, session_scope
        from magon_standalone.foundation.models import SupplierSourceRegistry
        from magon_standalone.foundation.settings import load_settings

        session_factory = create_session_factory(load_settings())
        with session_scope(session_factory) as session:
            registry = session.scalar(select(SupplierSourceRegistry).where(SupplierSourceRegistry.code == source_code))
            registry.config_json = {"source_label": "fixture_after_retry"}

        retried = self.client.post(
            f"/api/v1/operator/supplier-ingests/{ingest_code}/retry",
            headers=operator_headers,
            json={"reason_code": "manual_supplier_ingest_retry", "mode": "inline"},
        )
        self.assertEqual(retried.status_code, 200)

        detail = self.client.get(f"/api/v1/operator/supplier-ingests/{ingest_code}", headers=operator_headers)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["ingest"]["ingest_status"], "completed")
        self.assertEqual(detail.json()["ingest"]["retry_count"], 1)
        self.assertIsNone(detail.json()["ingest"]["failure_code"])
        self.assertGreaterEqual(len(detail.json()["raw_records"]), 1)

        audit = self.client.get("/api/v1/operator/audit/events", headers=operator_headers)
        self.assertEqual(audit.status_code, 200)
        actions = {item["action"] for item in audit.json()["items"]}
        self.assertIn("ingest_failed", actions)
        self.assertIn("ingest_completed", actions)

    def test_archive_hides_file_and_document_from_active_views(self):
        operator_headers = self._login("operator@example.com", "operator123")
        request_code, customer_ref = self._create_request()

        upload = self.client.post(
            "/api/v1/operator/files/upload",
            headers=operator_headers,
            data={
                "owner_type": "request",
                "owner_code": request_code,
                "file_type": "brief",
                "visibility_scope": "customer",
                "reason_code": "request_file_uploaded",
            },
            files={"upload": ("brief-archive.txt", b"archive-me", "text/plain")},
        )
        self.assertEqual(upload.status_code, 200)
        asset_code = upload.json()["item"]["code"]

        archive_file = self.client.post(
            f"/api/v1/operator/files/{asset_code}/archive",
            headers=operator_headers,
            json={"reason_code": "file_archived_manual"},
        )
        self.assertEqual(archive_file.status_code, 200)
        self.assertIsNotNone(archive_file.json()["item"]["archived_at"])

        operator_request = self.client.get(f"/api/v1/operator/requests/{request_code}", headers=operator_headers)
        self.assertEqual(operator_request.status_code, 200)
        self.assertEqual(operator_request.json()["item"]["managed_files"], [])

        public_request = self.client.get(f"/api/v1/public/requests/{customer_ref}")
        self.assertEqual(public_request.status_code, 200)
        self.assertEqual(public_request.json()["item"]["managed_files"], [])

        offer_code = self._create_offer(request_code, customer_ref, operator_headers)
        generated = self.client.post(
            "/api/v1/operator/documents/generate",
            headers=operator_headers,
            json={
                "owner_type": "offer",
                "owner_code": offer_code,
                "template_key": "offer_proposal",
                "reason_code": "offer_document_generated",
            },
        )
        self.assertEqual(generated.status_code, 200)
        document_code = generated.json()["item"]["code"]

        archive_document = self.client.post(
            f"/api/v1/operator/documents/{document_code}/archive",
            headers=operator_headers,
            json={"reason_code": "document_archived_manual"},
        )
        self.assertEqual(archive_document.status_code, 200)
        self.assertIsNotNone(archive_document.json()["item"]["archived_at"])

        public_request_after = self.client.get(f"/api/v1/public/requests/{customer_ref}")
        self.assertEqual(public_request_after.status_code, 200)
        self.assertEqual(public_request_after.json()["item"]["documents"], [])

        audit = self.client.get("/api/v1/operator/audit/events", headers=operator_headers)
        self.assertEqual(audit.status_code, 200)
        actions = {item["action"] for item in audit.json()["items"]}
        self.assertIn("file_archived", actions)
        self.assertIn("document_archived", actions)


if __name__ == "__main__":
    unittest.main()
