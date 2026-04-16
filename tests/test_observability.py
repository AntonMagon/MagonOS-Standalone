import os
import unittest
from unittest.mock import patch

from magon_standalone import observability


class TestObservability(unittest.TestCase):
    def test_backend_sentry_options_returns_none_without_dsn(self):
        with patch.dict(os.environ, {}, clear=True):
            # RU: Без DSN observability должна быть полностью пассивной, иначе локальный standalone runtime начнёт требовать внешний сервис.
            self.assertIsNone(observability.backend_sentry_options())

    def test_backend_sentry_options_reads_env(self):
        with patch.dict(
            os.environ,
            {
                "MAGON_SENTRY_DSN": "https://example@example.ingest.sentry.io/123",
                "MAGON_SENTRY_ENV": "staging",
                "MAGON_SENTRY_RELEASE": "abc123",
                "MAGON_SENTRY_TRACES_SAMPLE_RATE": "0.2",
                "MAGON_SENTRY_PROFILES_SAMPLE_RATE": "0.1",
            },
            clear=True,
        ):
            options = observability.backend_sentry_options()
            self.assertIsNotNone(options)
            self.assertEqual(options["environment"], "staging")
            self.assertEqual(options["release"], "abc123")
            self.assertEqual(options["traces_sample_rate"], 0.2)
            self.assertEqual(options["profiles_sample_rate"], 0.1)

    def test_wrap_wsgi_app_is_noop_without_dsn(self):
        with patch.dict(os.environ, {}, clear=True):
            sample = object()
            self.assertIs(observability.wrap_wsgi_app(sample), sample)


if __name__ == "__main__":
    unittest.main()
