import tempfile
import unittest
from pathlib import Path

from magon_standalone.operating_docs_sync import (
    AGENTS_SYNC_END,
    AGENTS_SYNC_START,
    README_SYNC_END,
    README_SYNC_START,
    sync_operating_docs,
)


class TestOperatingDocsSync(unittest.TestCase):
    def test_sync_operating_docs_renders_root_blocks_from_repo_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            # RU: Тестируем именно repo-native источник правды, чтобы AGENTS/README не зависели от ручного редактирования.
            (repo_root / "skills" / "demo-skill").mkdir(parents=True)
            (repo_root / "skills" / "demo-skill" / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: demo\n---\n",
                encoding="utf-8",
            )
            (repo_root / "docs").mkdir()
            (repo_root / ".codex").mkdir()
            (repo_root / "docs" / "current-project-state.md").write_text(
                """# Current Project State

## Validated standalone contour
- company
- opportunity

Also already standalone-owned:
- review queue

## Runtime surfaces
- public shell: `http://127.0.0.1:3000/`
""",
                encoding="utf-8",
            )
            (repo_root / ".codex" / "project-memory.md").write_text(
                """# Project Memory

## Active Context
<!-- ACTIVE:START -->
- Updated at: `2026-04-17 05:00 +07`
- Branch: `develop`
- Current focus: keep docs in sync
- Last verified workflow status: PASS `./scripts/verify_workflow.sh`
- Biggest operational risk: event-driven skill dispatch still does not exist
<!-- ACTIVE:END -->
""",
                encoding="utf-8",
            )
            (repo_root / "AGENTS.md").write_text(
                f"# AGENTS\n\n{AGENTS_SYNC_START}\nold\n{AGENTS_SYNC_END}\n",
                encoding="utf-8",
            )
            (repo_root / "README.md").write_text(
                f"# README\n\n{README_SYNC_START}\nold\n{README_SYNC_END}\n",
                encoding="utf-8",
            )

            synced = sync_operating_docs(repo_root)

            self.assertIn("keep docs in sync", synced[repo_root / "AGENTS.md"])
            self.assertIn("PASS `./scripts/verify_workflow.sh`", synced[repo_root / "README.md"])
            self.assertIn("demo-skill", synced[repo_root / "AGENTS.md"])
            self.assertIn("review queue", synced[repo_root / "README.md"])


if __name__ == "__main__":
    unittest.main()
