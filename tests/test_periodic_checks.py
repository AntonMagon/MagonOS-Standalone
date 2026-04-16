import unittest
from pathlib import Path

from magon_standalone.periodic_checks import build_lock_skip_payload, build_payload, build_result


class TestPeriodicChecks(unittest.TestCase):
    def test_build_payload_marks_success_when_all_commands_pass(self):
        payload = build_payload("manual", [build_result("sync", 0), build_result("smoke", 0)], generated_at="2026-04-17 10:00:00 +0700")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "manual")

    def test_build_payload_marks_failure_when_any_command_fails(self):
        payload = build_payload("launchd", [build_result("sync", 0), build_result("smoke", 1)], generated_at="2026-04-17 10:00:00 +0700")
        self.assertFalse(payload["ok"])

    def test_build_lock_skip_payload_is_not_a_failure(self):
        payload = build_lock_skip_payload("launchd", Path("/tmp/periodic-checks.lock"), generated_at="2026-04-17 10:00:00 +0700")
        # RU: Overlap отдельного periodic-run не должен красить статус в failure; это controlled skip, а не дефект репозитория.
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["skipped"])
        self.assertEqual(payload["results"][0]["command"], "periodic-lock-skip")


if __name__ == "__main__":
    unittest.main()
