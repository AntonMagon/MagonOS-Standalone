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


class TestFoundationFilesDocuments(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite+pysqlite:///{Path(self.tmpdir.name) / 'foundation.sqlite3'}"
        self.legacy_db_path = str(Path(self.tmpdir.name) / "legacy.sqlite3")
        self.storage_root = str(Path(self.tmpdir.name) / "storage")
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
                "MAGON_FOUNDATION_STORAGE_BACKEND",
                "MAGON_FOUNDATION_STORAGE_LOCAL_ROOT",
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
        os.environ["MAGON_FOUNDATION_STORAGE_BACKEND"] = "local"
        os.environ["MAGON_FOUNDATION_STORAGE_LOCAL_ROOT"] = self.storage_root

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
        draft = self.client.post(
            "/api/v1/public/draft-requests",
            json={
                "customer_email": "files-docs@example.com",
                "customer_name": "Files Docs",
                "title": "Files and documents request",
                "summary": "Need managed file/document contour verification.",
                "item_service_context": "Need request/offer/order managed assets without heavy editor.",
                "city": "Ho Chi Minh City",
                "requested_deadline_at": "2026-05-02T09:00:00+07:00",
                "intake_channel": "rfq_public",
                "honeypot": "",
                "elapsed_ms": 2100,
            },
        )
        self.assertEqual(draft.status_code, 200)
        draft_code = draft.json()["item"]["code"]
        submitted = self.client.post(
            f"/api/v1/public/draft-requests/{draft_code}/submit",
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
                "amount": 3200000,
                "currency_code": "VND",
                "lead_time_days": 8,
                "terms_text": "50% prepayment.",
                "scenario_type": "baseline",
                "supplier_ref": "SUPC-FILEDOC",
                "public_summary": "Managed file/doc offer",
                "comparison_title": "Managed baseline",
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

    def test_upload_new_version_checks_and_finalize(self):
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
            files={"upload": ("brief-v1.txt", b"brief-version-1", "text/plain")},
        )
        self.assertEqual(upload.status_code, 200)
        asset = upload.json()["item"]
        asset_code = asset["code"]
        self.assertEqual(asset["check_state"], "pending_review")
        self.assertEqual(asset["latest_version"]["version_no"], 1)

        v2 = self.client.post(
            f"/api/v1/operator/files/{asset_code}/versions",
            headers=operator_headers,
            data={"reason_code": "request_file_reuploaded"},
            files={"upload": ("brief-v2.txt", b"brief-version-2", "text/plain")},
        )
        self.assertEqual(v2.status_code, 200)
        self.assertEqual(v2.json()["item"]["latest_version"]["version_no"], 2)

        reviewed = self.client.post(
            f"/api/v1/operator/files/{asset_code}/review",
            headers=operator_headers,
            json={"target_state": "approved", "reason_code": "file_manual_review_approved"},
        )
        self.assertEqual(reviewed.status_code, 200)
        self.assertEqual(reviewed.json()["item"]["check_state"], "approved")

        finalized = self.client.post(
            f"/api/v1/operator/files/{asset_code}/finalize",
            headers=operator_headers,
            json={"reason_code": "file_final_version_confirmed"},
        )
        self.assertEqual(finalized.status_code, 200)
        self.assertTrue(finalized.json()["item"]["final_flag"])

        operator_request = self.client.get(f"/api/v1/operator/requests/{request_code}", headers=operator_headers)
        self.assertEqual(operator_request.status_code, 200)
        self.assertEqual(len(operator_request.json()["item"]["managed_files"]), 1)

        public_request = self.client.get(f"/api/v1/public/requests/{customer_ref}")
        self.assertEqual(public_request.status_code, 200)
        public_file = public_request.json()["item"]["managed_files"][0]
        self.assertTrue(public_file["final_flag"])
        file_download = self.client.get(public_file["download_url"].replace("/platform-api", ""))
        self.assertEqual(file_download.status_code, 200)
        self.assertEqual(file_download.content, b"brief-version-2")

    def test_document_generate_send_confirm_replace(self):
        operator_headers = self._login("operator@example.com", "operator123")
        request_code, customer_ref = self._create_request()
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
        self.assertEqual(generated.json()["item"]["current_version"]["version_no"], 1)

        sent = self.client.post(
            f"/api/v1/operator/documents/{document_code}/send",
            headers=operator_headers,
            json={"reason_code": "document_sent_to_customer"},
        )
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.json()["item"]["sent_state"], "sent")

        confirmed = self.client.post(
            f"/api/v1/operator/documents/{document_code}/confirm",
            headers=operator_headers,
            json={"reason_code": "document_confirmation_recorded"},
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["item"]["confirmation_state"], "confirmed")

        replaced = self.client.post(
            f"/api/v1/operator/documents/{document_code}/replace",
            headers=operator_headers,
            json={"reason_code": "document_replaced_after_revision"},
        )
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(replaced.json()["item"]["current_version_no"], 2)
        self.assertEqual(replaced.json()["item"]["sent_state"], "draft")
        self.assertEqual(replaced.json()["item"]["confirmation_state"], "pending")

        detail = self.client.get(f"/api/v1/operator/documents/{document_code}", headers=operator_headers)
        self.assertEqual(detail.status_code, 200)
        versions = detail.json()["versions"]
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0]["version_status"], "replaced")
        self.assertEqual(versions[1]["version_status"], "published")

        public_request = self.client.get(f"/api/v1/public/requests/{customer_ref}")
        self.assertEqual(public_request.status_code, 200)
        public_document = public_request.json()["item"]["documents"][0]
        document_download = self.client.get(public_document["download_url"].replace("/platform-api", ""))
        self.assertEqual(document_download.status_code, 200)
        self.assertIn(b"\xd0\x9a\xd0\xbe\xd0\xbc\xd0\xbc\xd0\xb5\xd1\x80\xd1\x87\xd0\xb5\xd1\x81\xd0\xba\xd0\xbe\xd0\xb5", document_download.content)


if __name__ == "__main__":
    unittest.main()
