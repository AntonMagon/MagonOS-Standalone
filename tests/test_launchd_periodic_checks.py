import tempfile
import unittest
from pathlib import Path

from magon_standalone.launchd_periodic_checks import render_launch_agent


class TestLaunchdPeriodicChecks(unittest.TestCase):
    def test_render_launch_agent_includes_repo_paths_and_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            launchd_root = repo_root / ".launchd-support" / "com.magonos.periodic-checks"
            program_path = launchd_root / "run-agent.sh"
            # RU: этот тест фиксирует новый launchd wrapper-контракт, чтобы CI поймал регресс сразу.
            # RU: Проверяем, что plist живёт в отдельном support-path и зовёт helper script,
            # а не снова привязывается к Desktop repo cwd/log path.
            rendered = render_launch_agent(
                repo_root,
                1800,
                launchd_root=launchd_root,
                program_path=program_path,
            )
            self.assertIn("com.magonos.periodic-checks", rendered)
            self.assertIn(str(launchd_root), rendered)
            self.assertIn(str(program_path), rendered)
            self.assertIn("<string>scripts/run_periodic_checks.py</string>", rendered)
            self.assertIn("<integer>1800</integer>", rendered)
            self.assertIn(str(launchd_root / "stdout.log"), rendered)
            self.assertIn(str(launchd_root / "stderr.log"), rendered)


if __name__ == "__main__":
    unittest.main()
