# RU: Эти тесты держат постоянный supplier parser/classifier в repo-aware scheduler-контуре, чтобы due live-ingest не зависел от ручного клика в UI.
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from alembic import command
from alembic.config import Config

from magon_standalone.foundation.db import create_session_factory, session_scope
from magon_standalone.foundation.models import SupplierRawIngest, SupplierSourceRegistry
from magon_standalone.foundation.settings import load_settings
from magon_standalone.foundation.supplier_scheduler import (
    build_supplier_source_schedule_state,
    enqueue_due_supplier_sources,
)
from magon_standalone.launchd_supplier_scheduler import render_supplier_scheduler_agent


def _apply_migrations(database_url: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    os.environ["MAGON_FOUNDATION_DATABASE_URL"] = database_url
    command.upgrade(config, "head")


class TestSupplierScheduler(unittest.TestCase):
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
                "MAGON_FOUNDATION_LEGACY_ENABLED",
                "MAGON_STANDALONE_DB_PATH",
                "MAGON_FOUNDATION_DEFAULT_ADMIN_EMAIL",
                "MAGON_FOUNDATION_DEFAULT_ADMIN_PASSWORD",
                "MAGON_FOUNDATION_DEFAULT_OPERATOR_EMAIL",
                "MAGON_FOUNDATION_DEFAULT_OPERATOR_PASSWORD",
                "MAGON_FOUNDATION_DEFAULT_CUSTOMER_EMAIL",
                "MAGON_FOUNDATION_DEFAULT_CUSTOMER_PASSWORD",
                "MAGON_FOUNDATION_LLM_ENABLED",
            ]
        }
        os.environ["MAGON_ENV"] = "test"
        os.environ["MAGON_FOUNDATION_DATABASE_URL"] = self.database_url
        os.environ["MAGON_FOUNDATION_REDIS_URL"] = ""
        os.environ["MAGON_FOUNDATION_CELERY_BROKER_URL"] = "memory://"
        os.environ["MAGON_FOUNDATION_CELERY_RESULT_BACKEND"] = "cache+memory://"
        os.environ["MAGON_FOUNDATION_LEGACY_ENABLED"] = "false"
        os.environ["MAGON_STANDALONE_DB_PATH"] = str(Path(self.tmpdir.name) / "legacy.sqlite3")
        os.environ["MAGON_FOUNDATION_DEFAULT_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["MAGON_FOUNDATION_DEFAULT_ADMIN_PASSWORD"] = "admin123"
        os.environ["MAGON_FOUNDATION_DEFAULT_OPERATOR_EMAIL"] = "operator@example.com"
        os.environ["MAGON_FOUNDATION_DEFAULT_OPERATOR_PASSWORD"] = "operator123"
        os.environ["MAGON_FOUNDATION_DEFAULT_CUSTOMER_EMAIL"] = "customer@example.com"
        os.environ["MAGON_FOUNDATION_DEFAULT_CUSTOMER_PASSWORD"] = "customer123"
        os.environ["MAGON_FOUNDATION_LLM_ENABLED"] = "true"

        _apply_migrations(self.database_url)
        from magon_standalone.foundation.bootstrap import seed_foundation

        settings = load_settings()
        session_factory = create_session_factory(settings)
        with session_scope(session_factory) as session:
            seed_foundation(session, settings)
        self.session_factory = session_factory

    def tearDown(self):
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_live_source_has_schedule_and_ai_assisted_classification_defaults(self):
        with session_scope(self.session_factory) as session:
            live_registry = session.query(SupplierSourceRegistry).filter_by(adapter_key="scenario_live").one()
            schedule = build_supplier_source_schedule_state(live_registry)

        self.assertTrue(schedule.enabled)
        self.assertEqual(schedule.interval_minutes, 60)
        self.assertEqual(schedule.reason_code, "scheduled_supplier_ingest")
        self.assertEqual(schedule.classification_mode, "ai_assisted_fallback")
        self.assertTrue(schedule.llm_enabled)
        self.assertTrue(schedule.due_now)

    def test_due_live_source_is_enqueued_once_and_fixture_is_skipped(self):
        fake_task = SimpleNamespace(id="celery-task-123")
        with patch("magon_standalone.foundation.supplier_scheduler.run_supplier_ingest.delay", return_value=fake_task):
            with session_scope(self.session_factory) as session:
                results = enqueue_due_supplier_sources(session)

            with session_scope(self.session_factory) as session:
                ingests = session.query(SupplierRawIngest).order_by(SupplierRawIngest.created_at.asc()).all()

        fixture_result = next(item for item in results if item["adapter_key"] == "fixture_json")
        live_result = next(item for item in results if item["adapter_key"] == "scenario_live")

        self.assertEqual(fixture_result["status"], "skipped")
        self.assertEqual(fixture_result["skip_reason"], "schedule_disabled")
        self.assertTrue(live_result["scheduled"])
        self.assertEqual(live_result["status"], "queued")
        self.assertEqual(live_result["classification_mode"], "ai_assisted_fallback")
        self.assertTrue(live_result["llm_enabled"])
        self.assertEqual(len(ingests), 1)
        self.assertEqual(ingests[0].trigger_mode, "scheduler_job")
        self.assertEqual(ingests[0].reason_code, "scheduled_supplier_ingest")
        self.assertEqual(ingests[0].task_id, "celery-task-123")

        with patch("magon_standalone.foundation.supplier_scheduler.run_supplier_ingest.delay", return_value=fake_task):
            with session_scope(self.session_factory) as session:
                repeated = enqueue_due_supplier_sources(session)
        repeated_live = next(item for item in repeated if item["adapter_key"] == "scenario_live")
        self.assertEqual(repeated_live["status"], "skipped")
        self.assertEqual(repeated_live["skip_reason"], "ingest_already_active")

    def test_render_launchd_supplier_scheduler_agent_uses_repo_runner(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            rendered = render_supplier_scheduler_agent(repo_root, 3600)
            self.assertIn("com.magonos.supplier-scheduler", rendered)
            self.assertIn(str(repo_root / "scripts" / "run_supplier_scheduler.py"), rendered)
            self.assertIn("<integer>3600</integer>", rendered)
            self.assertIn(str(repo_root / ".cache" / "launchd-supplier-scheduler.log"), rendered)


if __name__ == "__main__":
    unittest.main()
