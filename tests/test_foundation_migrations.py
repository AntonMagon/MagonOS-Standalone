# RU: Файл проверяет, что миграции первой волны поднимают полный acceptance-контур на чистой БД без ручного вмешательства.
# RU: Дополнительно держим эту проверку идемпотентной, чтобы CI ловил дрейф между несколькими upgrade head подряд.
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


class TestFoundationMigrations(unittest.TestCase):
    def test_upgrade_head_exposes_wave1_acceptance_columns_and_tables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database_url = f"sqlite+pysqlite:///{Path(tmpdir) / 'foundation.sqlite3'}"
            config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
            previous = os.environ.get("MAGON_FOUNDATION_DATABASE_URL")
            os.environ["MAGON_FOUNDATION_DATABASE_URL"] = database_url
            try:
                command.upgrade(config, "head")
                command.upgrade(config, "head")
            finally:
                if previous is None:
                    os.environ.pop("MAGON_FOUNDATION_DATABASE_URL", None)
                else:
                    os.environ["MAGON_FOUNDATION_DATABASE_URL"] = previous

            engine = create_engine(database_url)
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())

            self.assertIn("message_events", tables)
            self.assertIn("notification_rules", tables)
            self.assertIn("escalation_hints", tables)
            self.assertIn("supplier_raw_ingests", tables)

            ingest_columns = {column["name"] for column in inspector.get_columns("supplier_raw_ingests")}
            self.assertTrue({"failed_at", "last_retry_at", "retry_count", "failure_code", "failure_detail"}.issubset(ingest_columns))

            rule_columns = {column["name"] for column in inspector.get_columns("rules_engine_rules")}
            self.assertTrue({"rule_kind", "latest_version_no", "metadata_json"}.issubset(rule_columns))

            with engine.connect() as connection:
                version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            self.assertEqual(version, "20260417_0010")


if __name__ == "__main__":
    unittest.main()
