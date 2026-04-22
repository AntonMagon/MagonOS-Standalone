import tempfile
import unittest
from pathlib import Path

from magon_standalone.launchd_periodic_checks import render_launch_agent


class TestLaunchdPeriodicChecks(unittest.TestCase):
    def test_render_launch_agent_includes_repo_paths_and_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            # RU: этот тест фиксирует новый launchd wrapper-контракт, чтобы CI поймал регресс сразу.
            # RU: Проверяем не просто label, а то, что plist реально смотрит в versioned repo runner/log paths, а не в случайные внешние пути.
            rendered = render_launch_agent(repo_root, 1800)
            self.assertIn("com.magonos.periodic-checks", rendered)
            self.assertIn(str(repo_root / "scripts" / "run_launchd_repo_python.sh"), rendered)
            self.assertIn("<string>scripts/run_periodic_checks.py</string>", rendered)
            self.assertIn("<integer>1800</integer>", rendered)
            self.assertIn(str(repo_root / ".cache" / "launchd-periodic-checks.log"), rendered)


if __name__ == "__main__":
    unittest.main()
