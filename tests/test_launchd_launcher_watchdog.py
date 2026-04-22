import tempfile
import unittest
from pathlib import Path

from magon_standalone.launchd_launcher_watchdog import render_launcher_watchdog_agent


class TestLaunchdLauncherWatchdog(unittest.TestCase):
    def test_render_launcher_watchdog_agent_includes_repo_paths_and_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            # RU: этот тест страхует новый wrapper path, чтобы watchdog не деградировал обратно на прямой python call.
            # RU: Проверяем, что hourly watchdog смотрит в versioned repo runner/log paths,
            # иначе агент будет "жив", но перезапускать не тот launcher.
            rendered = render_launcher_watchdog_agent(repo_root, 3600)
            self.assertIn("com.magonos.launcher-watchdog", rendered)
            self.assertIn(str(repo_root / "scripts" / "run_launchd_repo_python.sh"), rendered)
            self.assertIn("<string>scripts/run_launcher_watchdog.py</string>", rendered)
            self.assertIn("<integer>3600</integer>", rendered)
            self.assertIn(str(repo_root / ".cache" / "launchd-launcher-watchdog.log"), rendered)


if __name__ == "__main__":
    unittest.main()
