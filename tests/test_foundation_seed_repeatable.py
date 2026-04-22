# RU: Этот regression-test держит repeatable seed живым: повторный bootstrap не должен ломаться на специальных scope вроде users:USR.
# RU: Repeatable seed нужен, чтобы launcher и smoke не зависели от случайного состояния базы.
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from magon_standalone.foundation.bootstrap import seed_foundation
from magon_standalone.foundation.db import create_session_factory, session_scope
from magon_standalone.foundation.settings import load_settings


class TestFoundationSeedRepeatable(unittest.TestCase):
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

        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")

    def tearDown(self):
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmpdir.cleanup()

    def test_seed_foundation_is_repeatable(self):
        settings = load_settings()
        session_factory = create_session_factory(settings)

        with session_scope(session_factory) as session:
            seed_foundation(session, settings)
        with session_scope(session_factory) as session:
            seed_foundation(session, settings)

        engine = create_engine(self.database_url, future=True)
        with engine.begin() as connection:
            user_count = connection.execute(text("SELECT COUNT(*) FROM users_access_users")).scalar_one()
            source_count = connection.execute(text("SELECT COUNT(*) FROM supplier_source_registries")).scalar_one()
            scope_count = connection.execute(
                text("SELECT COUNT(*) FROM foundation_sequences WHERE scope IN ('users:USR', 'supplier_source_registries')")
            ).scalar_one()

        self.assertEqual(user_count, 3)
        self.assertEqual(source_count, 2)
        self.assertEqual(scope_count, 2)


if __name__ == "__main__":
    unittest.main()
