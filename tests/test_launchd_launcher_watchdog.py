import tempfile
import unittest
from pathlib import Path

from magon_standalone.launchd_launcher_watchdog import render_launcher_watchdog_agent


class TestLaunchdLauncherWatchdog(unittest.TestCase):
    def test_render_launcher_watchdog_agent_includes_repo_paths_and_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            launchd_root = repo_root / ".launchd-support" / "com.magonos.launcher-watchdog"
            program_path = launchd_root / "run-agent.sh"
            # RU: этот тест страхует новый wrapper path, чтобы watchdog не деградировал обратно на прямой python call.
            # RU: Теперь plist обязан жить в отдельном launchd-support path и звать helper script,
            # иначе macOS снова упрётся в Desktop/TCC вместо реального старта watchdog.
            rendered = render_launcher_watchdog_agent(
                repo_root,
                3600,
                launchd_root=launchd_root,
                program_path=program_path,
            )
            self.assertIn("com.magonos.launcher-watchdog", rendered)
            self.assertIn(str(launchd_root), rendered)
            self.assertIn(str(program_path), rendered)
            self.assertIn("<string>scripts/run_launcher_watchdog.py</string>", rendered)
            self.assertIn("<integer>3600</integer>", rendered)
            self.assertIn(str(launchd_root / "stdout.log"), rendered)
            self.assertIn(str(launchd_root / "stderr.log"), rendered)


if __name__ == "__main__":
    unittest.main()
