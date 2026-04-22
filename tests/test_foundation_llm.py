# RU: Эти тесты держат LLM-контур первой волны explainable и env-gated: без ключа он не должен ломать runtime, а с адаптером должен подключаться в текущий ai_assisted fallback.
# RU: LLM здесь остаётся вспомогательным parsing fallback и не забирает на себя workflow-решения.
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from magon_standalone.foundation.app import create_app
from magon_standalone.supplier_intelligence.extraction_engine import ScenarioExtractionEngine
from magon_standalone.supplier_intelligence.scenario_config import ScenarioConfig


def _apply_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    os.environ["MAGON_FOUNDATION_DATABASE_URL"] = database_url
    command.upgrade(config, "head")


class TestFoundationLlm(unittest.TestCase):
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
                "MAGON_FOUNDATION_LLM_ENABLED",
                "OPENAI_API_KEY",
                "MAGON_FOUNDATION_LLM_MODEL",
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
        os.environ["MAGON_FOUNDATION_LLM_ENABLED"] = "false"
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ["MAGON_FOUNDATION_LLM_MODEL"] = "gpt-5.2"

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

    def test_llm_status_reports_disabled_by_default(self):
        operator_headers = self._login("operator@example.com", "operator123")
        response = self.client.get("/api/v1/operator/llm/status", headers=operator_headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["enabled"])
        self.assertFalse(payload["configured"])
        self.assertEqual(payload["health"]["detail"], "llm_disabled")

    def test_llm_preview_uses_adapter_when_configured(self):
        operator_headers = self._login("operator@example.com", "operator123")
        fake_adapter = SimpleNamespace(
            configured=True,
            extract_supplier_preview=lambda **_: SimpleNamespace(
                adapter="openai_responses",
                model="gpt-5.2",
                raw_text='{"company_name":"LLM Vendor","confidence":0.72}',
                parsed_json={"company_name": "LLM Vendor", "confidence": 0.72},
            ),
        )
        with patch("magon_standalone.foundation.modules.llm.get_llm_adapter", return_value=fake_adapter):
            response = self.client.post(
                "/api/v1/operator/llm/extract-preview",
                headers=operator_headers,
                json={
                    "page_url": "https://example.com/vendor",
                    "query": "label printing vietnam",
                    "text_blob": "LLM Vendor provides label printing in Ho Chi Minh City with email sales@example.com",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parsed_json"]["company_name"], "LLM Vendor")

    def test_ai_assisted_extraction_prefers_llm_preview_when_available(self):
        engine = ScenarioExtractionEngine(ScenarioConfig.load())
        fake_adapter = SimpleNamespace(
            configured=True,
            extract_supplier_preview=lambda **_: SimpleNamespace(
                adapter="openai_responses",
                model="gpt-5.2",
                raw_text='{"company_name":"Saigon Flexo Print","city":"Ho Chi Minh City","phones":["+842812345678"],"emails":["sales@flexo.vn"],"categories":["flexo"],"services":["flexo printing"],"products":["labels"],"contact_persons":["Ms. Lan"],"confidence":0.74,"explanation":"Parsed from fallback text"}',
                parsed_json={
                    "company_name": "Saigon Flexo Print",
                    "city": "Ho Chi Minh City",
                    "phones": ["+842812345678"],
                    "emails": ["sales@flexo.vn"],
                    "categories": ["flexo"],
                    "services": ["flexo printing"],
                    "products": ["labels"],
                    "contact_persons": ["Ms. Lan"],
                    "confidence": 0.74,
                    "explanation": "Parsed from fallback text",
                },
            ),
        )
        with patch("magon_standalone.supplier_intelligence.extraction_engine.get_llm_adapter", return_value=fake_adapter):
            records = engine.extract_ai_assisted(
                page_url="https://example.com/vendor",
                html="<html><body><h1>Fallback vendor</h1><p>Label printing in Ho Chi Minh City</p></body></html>",
                route={"scenario_key": "HARD_DYNAMIC_OR_BLOCKED", "reasons": ["blocked"], "execution_flags": {}},
                query="label printing vietnam",
            )
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["company_name"], "Saigon Flexo Print")
        self.assertEqual(record["phones"], ["+842812345678"])
        self.assertEqual(record["evidence_payloads"][0]["metadata"]["fallback"], "openai_responses")
        self.assertEqual(record["raw_payload"]["llm_explanation"], "Parsed from fallback text")
