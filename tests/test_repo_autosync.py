import tempfile
import unittest
from pathlib import Path

from magon_standalone.repo_autosync import build_auto_plan, plan_commands


class TestRepoAutosync(unittest.TestCase):
    def test_build_auto_plan_uses_web_verify_for_web_changes(self):
        plan = build_auto_plan(["apps/web/app/page.tsx"])
        self.assertTrue(plan.sync_root_docs)
        self.assertTrue(plan.sync_visual_map)
        self.assertEqual(plan.verify_mode, "web")

    def test_build_auto_plan_uses_base_verify_for_backend_changes(self):
        plan = build_auto_plan(["src/magon_standalone/repo_autosync.py"])
        self.assertEqual(plan.verify_mode, "base")

    def test_build_auto_plan_uses_fallback_for_empty_changes(self):
        plan = build_auto_plan([])
        self.assertEqual(plan.verify_mode, "base")
        self.assertEqual(plan.changed_paths, ())

    def test_build_auto_plan_ignores_generated_outputs_to_avoid_loops(self):
        # RU: Generated outputs не должны триггерить новый autosync-run, иначе watcher уходит в бесконечный цикл.
        plan = build_auto_plan(["docs/ru/visuals/project-map.md", "README.md"])
        self.assertFalse(plan.sync_root_docs)
        self.assertFalse(plan.sync_visual_map)
        self.assertEqual(plan.verify_mode, "none")

    def test_build_auto_plan_ignores_python_cache_noise(self):
        plan = build_auto_plan(
            [
                "src/magon_standalone/__pycache__/repo_autosync.cpython-310.pyc",
                "scripts/__pycache__",
            ]
        )
        self.assertFalse(plan.sync_root_docs)
        self.assertFalse(plan.sync_visual_map)
        self.assertEqual(plan.verify_mode, "none")

    def test_plan_commands_orders_sync_before_verify(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            plan = build_auto_plan(["tests/test_repo_autosync.py"])
            commands = plan_commands(repo_root, plan)
            self.assertEqual(commands[0], [str(repo_root / ".venv" / "bin" / "python"), "scripts/sync_operating_docs.py"])
            self.assertEqual(commands[1], [str(repo_root / ".venv" / "bin" / "python"), "scripts/update_project_visual_map.py"])
            self.assertEqual(commands[2], ["./scripts/verify_workflow.sh"])


if __name__ == "__main__":
    unittest.main()
